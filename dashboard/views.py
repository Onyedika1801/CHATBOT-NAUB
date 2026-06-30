from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages as django_messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import datetime
import re

from chatbot.models import ConversationLog, UnansweredQuestion, KnowledgeBaseEntry, ChatSession
from chatbot.nlp_engine import get_matcher


def is_staff_user(user):
    return user.is_active and user.is_staff


@user_passes_test(is_staff_user, login_url='/accounts/login/')
def dashboard_home(request):
    total_questions = ConversationLog.objects.count()
    answered_count = ConversationLog.objects.filter(status="answered").count()
    unanswered_count = ConversationLog.objects.filter(status="unanswered").count()
    rejected_count = ConversationLog.objects.filter(status="rejected").count()

    accuracy = round((answered_count / total_questions) * 100, 2) if total_questions else 0.0
    avg_similarity = ConversationLog.objects.filter(status="answered").aggregate(avg=Avg("similarity_score"))["avg"]
    avg_similarity = round(avg_similarity * 100, 2) if avg_similarity else 0.0

    pending_unanswered = UnansweredQuestion.objects.filter(status="pending").order_by("-times_asked", "-created_at")
    recent_logs = ConversationLog.objects.select_related("matched_intent").order_by("-created_at")[:15]

    top_intents = (
        KnowledgeBaseEntry.objects.filter(times_matched__gt=0)
        .order_by("-times_matched")[:8]
    )

    total_sessions = ChatSession.objects.count()
    total_kb_entries = KnowledgeBaseEntry.objects.filter(is_active=True).count()

    # 7-day trend for the chart
    today = timezone.now().date()
    trend = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_qs = ConversationLog.objects.filter(created_at__date=day)
        trend.append({
            "label": day.strftime("%a"),
            "answered": day_qs.filter(status="answered").count(),
            "unanswered": day_qs.filter(status="unanswered").count(),
        })

    context = {
        "active": "home",
        "total_questions": total_questions,
        "answered_count": answered_count,
        "unanswered_count": unanswered_count,
        "rejected_count": rejected_count,
        "accuracy": accuracy,
        "avg_similarity": avg_similarity,
        "pending_unanswered": pending_unanswered,
        "recent_logs": recent_logs,
        "top_intents": top_intents,
        "total_sessions": total_sessions,
        "total_kb_entries": total_kb_entries,
        "trend": trend,
    }
    return render(request, "dashboard/home.html", context)


@user_passes_test(is_staff_user, login_url='/accounts/login/')
def unanswered_list(request):
    status_filter = request.GET.get("status", "pending")
    qs = UnansweredQuestion.objects.all()
    if status_filter != "all":
        qs = qs.filter(status=status_filter)
    qs = qs.order_by("-times_asked", "-created_at")
    return render(request, "dashboard/unanswered_list.html", {
        "active": "unanswered",
        "unanswered_questions": qs,
        "status_filter": status_filter,
    })


def _slugify_intent(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "intent"


@user_passes_test(is_staff_user, login_url='/accounts/login/')
@require_POST
def answer_question(request, pk):
    """Admin provides an answer to a pending unanswered question. This creates
    (or updates) a KnowledgeBaseEntry so the answer is shown automatically the
    next time any user asks that question, and rebuilds the matcher."""
    uq = get_object_or_404(UnansweredQuestion, pk=pk)
    answer_text = request.POST.get("answer", "").strip()
    link_to_existing = request.POST.get("link_to_existing_id")

    if not answer_text and not link_to_existing:
        django_messages.error(request, "Please provide an answer or link to an existing topic.")
        return redirect('dashboard:unanswered_list')

    if link_to_existing:
        kb_entry = get_object_or_404(KnowledgeBaseEntry, pk=link_to_existing)
        existing_questions = kb_entry.questions
        kb_entry.questions = existing_questions + "\n" + uq.question
        kb_entry.save(update_fields=["questions"])
    else:
        base_slug = _slugify_intent(uq.question[:40])
        slug = base_slug
        counter = 1
        while KnowledgeBaseEntry.objects.filter(intent_id=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"

        kb_entry = KnowledgeBaseEntry.objects.create(
            intent_id=slug,
            questions=uq.question,
            answer=answer_text,
            category="admin-added",
            is_active=True,
        )

    uq.status = "answered"
    uq.admin_answer = answer_text or kb_entry.answer
    uq.linked_kb_entry = kb_entry
    uq.answered_by = request.user
    uq.answered_at = timezone.now()
    uq.save()

    if uq.log_entry:
        uq.log_entry.status = "answered"
        uq.log_entry.matched_intent = kb_entry
        uq.log_entry.answer_given = kb_entry.answer
        uq.log_entry.save(update_fields=["status", "matched_intent", "answer_given"])

    get_matcher(force_rebuild=True)

    django_messages.success(request, "Answer saved. The chatbot will now answer this question automatically.")
    return redirect('dashboard:unanswered_list')


@user_passes_test(is_staff_user, login_url='/accounts/login/')
@require_POST
def ignore_question(request, pk):
    uq = get_object_or_404(UnansweredQuestion, pk=pk)
    uq.status = "ignored"
    uq.save(update_fields=["status"])
    django_messages.info(request, "Question marked as ignored.")
    return redirect('dashboard:unanswered_list')


@user_passes_test(is_staff_user, login_url='/accounts/login/')
def knowledge_base_list(request):
    entries = KnowledgeBaseEntry.objects.all().order_by("-times_matched")
    return render(request, "dashboard/kb_list.html", {"active": "kb", "entries": entries})


@user_passes_test(is_staff_user, login_url='/accounts/login/')
@require_POST
def kb_toggle_active(request, pk):
    entry = get_object_or_404(KnowledgeBaseEntry, pk=pk)
    entry.is_active = not entry.is_active
    entry.save(update_fields=["is_active"])
    get_matcher(force_rebuild=True)
    return redirect('dashboard:kb_list')


@user_passes_test(is_staff_user, login_url='/accounts/login/')
def conversation_logs(request):
    status_filter = request.GET.get("status", "all")
    qs = ConversationLog.objects.select_related("matched_intent", "user").order_by("-created_at")
    if status_filter != "all":
        qs = qs.filter(status=status_filter)
    return render(request, "dashboard/logs.html", {"active": "logs", "logs": qs[:200], "status_filter": status_filter})

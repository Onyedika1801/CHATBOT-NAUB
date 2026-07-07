from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages as django_messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import datetime
import re

from chatbot.models import ConversationLog, UnansweredQuestion, KnowledgeBaseEntry, ChatSession
from chatbot.nlp_engine import get_matcher
from accounts.signals import MAX_ADMIN_ACCOUNTS


def is_staff_user(user):
    return user.is_active and user.is_staff


def is_superuser(user):
    return user.is_active and user.is_superuser


@user_passes_test(is_superuser, login_url='/accounts/login/')
def manage_admins(request):
    """Superuser-only page to view current admin accounts and create new
    ones, without needing to know about Django's separate /admin/ panel.
    Enforces the same 3-admin cap and unique-email rule as everywhere else."""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password", "")
            make_superuser = request.POST.get("is_superuser") == "on"

            errors = []
            if not username or not email or not password:
                errors.append("Username, email, and password are all required.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if username and User.objects.filter(username__iexact=username).exists():
                errors.append(f"The username '{username}' is already taken.")
            if email and User.objects.filter(email__iexact=email).exists():
                errors.append(f"An account with the email '{email}' already exists.")

            current_admin_count = User.objects.filter(is_staff=True).count()
            if current_admin_count >= MAX_ADMIN_ACCOUNTS:
                errors.append(
                    f"Admin accounts are capped at {MAX_ADMIN_ACCOUNTS}. "
                    f"Demote or delete an existing admin first."
                )

            if errors:
                for e in errors:
                    django_messages.error(request, e)
            else:
                try:
                    new_admin = User(
                        username=username,
                        email=email,
                        is_staff=True,
                        is_superuser=make_superuser,
                        is_active=True,
                    )
                    new_admin.set_password(password)
                    new_admin.full_clean()
                    new_admin.save()
                    django_messages.success(request, f"Admin account '{username}' created successfully.")
                except ValidationError as e:
                    for msg in e.messages:
                        django_messages.error(request, msg)

        elif action == "toggle_active":
            target = get_object_or_404(User, pk=request.POST.get("user_id"))
            if target.pk == request.user.pk:
                django_messages.error(request, "You cannot deactivate your own account.")
            else:
                target.is_active = not target.is_active
                target.save(update_fields=["is_active"])
                django_messages.success(request, f"{target.username} is now {'active' if target.is_active else 'deactivated'}.")

        elif action == "revoke":
            target = get_object_or_404(User, pk=request.POST.get("user_id"))
            if target.pk == request.user.pk:
                django_messages.error(request, "You cannot revoke your own admin access.")
            else:
                target.is_staff = False
                target.is_superuser = False
                target.save(update_fields=["is_staff", "is_superuser"])
                django_messages.success(request, f"Admin access revoked for {target.username}.")

        return redirect('dashboard:manage_admins')

    admins = User.objects.filter(is_staff=True).order_by("-is_superuser", "username")
    return render(request, "dashboard/manage_admins.html", {
        "active": "admins",
        "admins": admins,
        "max_admins": MAX_ADMIN_ACCOUNTS,
        "slots_used": admins.count(),
    })


@user_passes_test(is_staff_user, login_url='/accounts/login/')
def dashboard_home(request):
    total_questions = ConversationLog.objects.count()
    answered_count = ConversationLog.objects.filter(status="answered").count()
    clarification_count = ConversationLog.objects.filter(status="clarification").count()
    unanswered_count = ConversationLog.objects.filter(status="unanswered").count()

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
        "clarification_count": clarification_count,
        "unanswered_count": unanswered_count,
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
    alt_phrasings_raw = request.POST.get("alt_phrasings", "").strip()
    alt_phrasings = [p.strip() for p in alt_phrasings_raw.splitlines() if p.strip()]

    if not answer_text and not link_to_existing:
        django_messages.error(request, "Please provide an answer or link to an existing topic.")
        return redirect('dashboard:unanswered_list')

    if link_to_existing:
        kb_entry = get_object_or_404(KnowledgeBaseEntry, pk=link_to_existing)
        extra_lines = [uq.question] + alt_phrasings
        kb_entry.questions = kb_entry.questions + "\n" + "\n".join(extra_lines)
        kb_entry.save(update_fields=["questions"])
    else:
        base_slug = _slugify_intent(uq.question[:40])
        slug = base_slug
        counter = 1
        while KnowledgeBaseEntry.objects.filter(intent_id=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"

        all_questions = "\n".join([uq.question] + alt_phrasings)
        kb_entry = KnowledgeBaseEntry.objects.create(
            intent_id=slug,
            questions=all_questions,
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


@user_passes_test(is_superuser, login_url='/accounts/login/')
def kb_create(request):
    """Lets a superuser add a brand-new knowledge base entry directly,
    without needing a student to have asked it first (unlike the
    Unanswered Questions flow, which only surfaces questions after
    someone actually asks them)."""
    if request.method == "POST":
        questions_raw = request.POST.get("questions", "").strip()
        answer = request.POST.get("answer", "").strip()
        category = request.POST.get("category", "").strip() or "general"
        map_query = request.POST.get("map_query", "").strip()

        questions = [q.strip() for q in questions_raw.splitlines() if q.strip()]

        errors = []
        if not questions:
            errors.append("Please provide at least one training question.")
        if not answer:
            errors.append("Please provide the answer.")

        if errors:
            for e in errors:
                django_messages.error(request, e)
            return render(request, "dashboard/kb_create.html", {
                "active": "kb",
                "questions_raw": questions_raw,
                "answer": answer,
                "category": category,
                "map_query": map_query,
            })

        base_slug = _slugify_intent(questions[0][:40])
        slug = base_slug
        counter = 1
        while KnowledgeBaseEntry.objects.filter(intent_id=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"

        KnowledgeBaseEntry.objects.create(
            intent_id=slug,
            questions="\n".join(questions),
            answer=answer,
            category=category,
            map_query=map_query,
            is_active=True,
        )
        get_matcher(force_rebuild=True)
        django_messages.success(request, f"New knowledge base entry '{slug}' created.")
        return redirect('dashboard:kb_list')

    return render(request, "dashboard/kb_create.html", {"active": "kb"})


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

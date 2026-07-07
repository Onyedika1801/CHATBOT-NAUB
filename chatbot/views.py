import hashlib
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import ChatSession, ConversationLog, UnansweredQuestion
from .nlp_engine import is_gibberish, get_matcher

GIBBERISH_RESPONSE = (
    "I'm sorry, I didn't quite understand that. 🤔 Could you please rephrase your "
    "question using complete words? For example, try asking about admissions, "
    "school fees, hostel accommodation, or the academic calendar."
)


def _anon_key(request):
    """Stable anonymous identifier for guests, derived from the Django session key."""
    if not request.session.session_key:
        request.session.create()
    raw = request.session.session_key
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _get_or_create_active_session(request):
    if request.user.is_authenticated:
        session = ChatSession.objects.filter(user=request.user, is_active=True).first()
        if not session:
            session = ChatSession.objects.create(user=request.user, is_active=True)
        return session
    else:
        anon_key = _anon_key(request)
        session = ChatSession.objects.filter(anonymous_key=anon_key, is_active=True).first()
        if not session:
            session = ChatSession.objects.create(anonymous_key=anon_key, is_active=True)
        return session


def chat_view(request):
    """Renders the main chat UI. The active session's messages are shown;
    older logs remain in the database but are not displayed once a new chat starts."""
    session = _get_or_create_active_session(request)
    messages = session.messages.order_by("created_at")
    return render(request, "chatbot/chat.html", {
        "session": session,
        "messages": messages,
    })


@require_POST
def send_message(request):
    """AJAX endpoint: receives a user question, runs gibberish check then
    TF-IDF/Cosine Similarity matching, logs appropriately, and returns the bot reply."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    question = (payload.get("message") or "").strip()
    if not question:
        return JsonResponse({"error": "Empty message."}, status=400)

    session = _get_or_create_active_session(request)

    # Rule 4: gibberish detection - reject BEFORE storing in the database
    if is_gibberish(question):
        return JsonResponse({
            "reply": GIBBERISH_RESPONSE,
            "status": "rejected",
            "stored": False,
        })

    matcher = get_matcher()
    result = matcher.match(question)

    user = request.user if request.user.is_authenticated else None

    log = ConversationLog.objects.create(
        session=session,
        user=user,
        question=question,
        matched_intent=result["entry"],
        answer_given=result["answer"] or "",
        similarity_score=result["similarity_score"],
        status=result["status"],
    )

    candidates = []
    map_query = None

    if result["status"] == "answered":
        entry = result["entry"]
        entry.times_matched += 1
        entry.save(update_fields=["times_matched"])
        reply_text = result["answer"]
        map_query = entry.map_query or None

    elif result["status"] == "clarification":
        reply_text = "I found a few things that might match. Which one did you mean?"
        candidates = result["candidates"]

    else:
        reply_text = (
            "I don't have an answer for that right now. Please check back later."
        )
        uq, created = UnansweredQuestion.objects.get_or_create(
            question__iexact=question,
            status="pending",
            defaults={"question": question, "log_entry": log},
        )
        if not created:
            uq.times_asked += 1
            if not uq.log_entry:
                uq.log_entry = log
            uq.save(update_fields=["times_asked", "log_entry"])

    return JsonResponse({
        "reply": reply_text,
        "status": result["status"],
        "similarity_score": result["similarity_score"],
        "candidates": candidates,
        "map_query": map_query,
        "stored": True,
    })


@require_POST
def new_chat(request):
    """Rule 3: Starting a new chat clears/deactivates the visible previous chat,
    but all messages remain permanently in ConversationLog for analytics."""
    if request.user.is_authenticated:
        ChatSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
        session = ChatSession.objects.create(user=request.user, is_active=True)
    else:
        anon_key = _anon_key(request)
        ChatSession.objects.filter(anonymous_key=anon_key, is_active=True).update(is_active=False)
        session = ChatSession.objects.create(anonymous_key=anon_key, is_active=True)

    return JsonResponse({"session_id": str(session.session_id)})

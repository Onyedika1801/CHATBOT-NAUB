import uuid
from django.db import models
from django.contrib.auth.models import User


class KnowledgeBaseEntry(models.Model):
    """A single intent in the knowledge base: a set of training questions and one answer."""
    intent_id = models.SlugField(max_length=100, unique=True)
    questions = models.TextField(
        help_text="One training question/phrase per line, used to train the TF-IDF matcher."
    )
    answer = models.TextField()
    category = models.CharField(max_length=100, blank=True, default="general")
    map_query = models.CharField(
        max_length=255, blank=True,
        help_text="Optional: an address or place name (e.g. '1 Gombe Road, Biu, Borno State, Nigeria') "
                   "to show an embedded Google Map alongside this answer. Leave blank for no map."
    )
    is_active = models.BooleanField(default=True)
    times_matched = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Knowledge Base Entry"
        verbose_name_plural = "Knowledge Base Entries"
        ordering = ["intent_id"]

    def __str__(self):
        return self.intent_id

    def question_list(self):
        return [q.strip() for q in self.questions.splitlines() if q.strip()]


class ChatSession(models.Model):
    """Represents one chat session/window for a user. Creating a new chat clears the
    active session shown to the user, but the ConversationLog history is preserved
    permanently for analytics."""
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="chat_sessions")
    anonymous_key = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        owner = self.user.username if self.user else f"anon:{self.anonymous_key}"
        return f"Session {self.session_id} ({owner})"


class ConversationLog(models.Model):
    """Permanent log of every valid question asked, regardless of chat session resets."""
    MATCH_STATUS_CHOICES = (
        ("answered", "Answered"),
        ("clarification", "Clarification Requested"),
        ("unanswered", "Unanswered / Low Confidence"),
        ("rejected", "Rejected (Gibberish/Invalid)"),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversation_logs")
    question = models.TextField()
    matched_intent = models.ForeignKey(
        KnowledgeBaseEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="matched_logs"
    )
    answer_given = models.TextField(blank=True)
    similarity_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default="unanswered")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.question[:50]}"


class UnansweredQuestion(models.Model):
    """Queue of questions the bot could not confidently answer, awaiting admin review."""
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("answered", "Answered"),
        ("ignored", "Ignored"),
    )

    log_entry = models.OneToOneField(
        ConversationLog, on_delete=models.CASCADE, related_name="unanswered_record", null=True, blank=True
    )
    question = models.TextField()
    times_asked = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_answer = models.TextField(blank=True)
    linked_kb_entry = models.ForeignKey(
        KnowledgeBaseEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_from"
    )
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-times_asked", "-created_at"]

    def __str__(self):
        return f"({self.status}) {self.question[:50]}"

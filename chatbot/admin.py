from django.contrib import admin
from .models import KnowledgeBaseEntry, ChatSession, ConversationLog, UnansweredQuestion


@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):
    list_display = ("intent_id", "category", "times_matched", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("intent_id", "questions", "answer")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "user", "anonymous_key", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ("question", "status", "similarity_score", "matched_intent", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("question",)


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "status", "times_asked", "created_at")
    list_filter = ("status",)
    search_fields = ("question",)

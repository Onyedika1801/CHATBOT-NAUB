import json
from pathlib import Path
from django.core.management.base import BaseCommand
from chatbot.models import KnowledgeBaseEntry


class Command(BaseCommand):
    help = "Load/refresh the NAUB knowledge base from chatbot/knowledge_base.json"

    def handle(self, *args, **options):
        kb_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created, updated = 0, 0
        for item in data:
            questions_text = "\n".join(item.get("questions", []))
            obj, was_created = KnowledgeBaseEntry.objects.update_or_create(
                intent_id=item["id"],
                defaults={
                    "questions": questions_text,
                    "answer": item["answer"],
                    "category": item.get("category", "general"),
                    "map_query": item.get("map_query", ""),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Knowledge base loaded: {created} created, {updated} updated."))

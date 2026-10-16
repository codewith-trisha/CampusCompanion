from django.core.management.base import BaseCommand

from core.models import CollegeInformation
from core import rag_engine


class Command(BaseCommand):
    help = "Embeds every CollegeInformation row and stores it in the ChromaDB vector index."

    def handle(self, *args, **options):
        entries = CollegeInformation.objects.all()
        total = entries.count()

        if total == 0:
            self.stdout.write(self.style.WARNING(
                "No CollegeInformation rows found. Run `python manage.py seed_data` first."
            ))
            return

        self.stdout.write(f"Embedding {total} documents (first run downloads the embedding model, ~90MB)...")

        for i, entry in enumerate(entries, start=1):
            rag_engine.index_document(
                doc_id=entry.id,
                title=entry.title,
                content=entry.content,
                category=entry.category,
            )
            self.stdout.write(f"  [{i}/{total}] indexed: {entry.title}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! {total} documents indexed into the vector store."))

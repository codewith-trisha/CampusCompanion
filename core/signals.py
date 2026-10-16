from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import CollegeInformation
from .rag_engine import index_document, _get_collection


@receiver(post_save, sender=CollegeInformation)
def update_vector(sender, instance, **kwargs):
    """
    Whenever a CollegeInformation object is created or edited,
    automatically update its embedding in ChromaDB.
    """

    index_document(
        doc_id=instance.id,
        title=instance.title,
        content=instance.content,
        category=instance.category,
    )


@receiver(post_delete, sender=CollegeInformation)
def delete_vector(sender, instance, **kwargs):
    """
    Remove the embedding if a document is deleted.
    """

    collection = _get_collection()
    collection.delete(ids=[str(instance.id)])
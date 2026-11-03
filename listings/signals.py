"""
Django never deletes the underlying file in storage when a model row
with a FileField/ImageField is deleted -- that's deliberate upstream
behavior (the same file could in principle be referenced elsewhere),
but for this project it just means deleted products/accounts/removed
photos leave orphaned files in media/ forever. These signal handlers
clean that up for the three image fields in this app: ListingImage,
Category.icon, and (registered from the accounts app) User.profile_picture.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Category, ListingImage


def _delete_file_field(file_field):
    if file_field and file_field.name:
        file_field.storage.delete(file_field.name)


@receiver(post_delete, sender=ListingImage)
def delete_listing_image_file(sender, instance, **kwargs):
    _delete_file_field(instance.image)


@receiver(post_delete, sender=Category)
def delete_category_icon_file(sender, instance, **kwargs):
    _delete_file_field(instance.icon)

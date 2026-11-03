from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import User


@receiver(post_delete, sender=User)
def delete_profile_picture_file(sender, instance, **kwargs):
    if instance.profile_picture and instance.profile_picture.name:
        instance.profile_picture.storage.delete(instance.profile_picture.name)

import logging

from django.core.exceptions import ValidationError
from django.forms import ImageField

from kazeb.imaging import compress_uploaded_image

from .models import ListingImage

logger = logging.getLogger(__name__)


def validate_listing_images(image_files):
    image_field = ImageField()
    errors = []
    for image_file in image_files:
        try:
            image_field.clean(image_file)
        except ValidationError as error:
            errors.extend(error.messages)
    return errors


def save_listing_images(listing, image_files, created_images, *, cover_first_image):
    for index, image_file in enumerate(image_files):
        image = ListingImage(
            listing=listing,
            is_cover=cover_first_image and index == 0,
        )
        image.image = compress_uploaded_image(image_file)
        created_images.append(image)
        image.save()


def ensure_listing_cover(listing):
    images = listing.images.order_by("pk")
    if images.filter(is_cover=True).exists():
        return True

    first_image = images.first()
    if first_image is None:
        return False

    images.filter(pk=first_image.pk).update(is_cover=True)
    return True


def cleanup_uploaded_listing_images(images):
    for image in images:
        image_file = image.image
        if not image_file or not image_file.name or not image_file._committed:
            continue
        try:
            image_file.storage.delete(image_file.name)
        except Exception:
            logger.exception(
                "Could not clean up uploaded listing image %s after rollback.",
                image_file.name,
            )

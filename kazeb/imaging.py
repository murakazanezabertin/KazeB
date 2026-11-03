"""
Resizes/compresses an uploaded image in place before it's saved to
storage, so a seller uploading a full-resolution phone photo (often
3-8MB) doesn't slow down every page that shows it or burn through
storage and bandwidth. Called at the point of upload (in the views
that handle listing photos and profile pictures), not from a model
save() override, so it only runs once per upload rather than on every
unrelated save of the same row.
"""

import io

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def compress_uploaded_image(django_file, max_dimension=1600, quality=82):
    """
    Takes an UploadedFile (from request.FILES), returns a new
    ContentFile with the image resized to fit within
    max_dimension x max_dimension and re-encoded, preserving
    transparency for PNGs and using JPEG for everything else.
    Returns the original file unchanged if it isn't a readable image
    (defensive -- an upload that isn't really an image shouldn't crash
    the request; the ImageField's own validation handles rejecting it).
    """
    try:
        image = Image.open(django_file)
        image = ImageOps.exif_transpose(image)  # respect phone camera orientation
    except Exception:
        django_file.seek(0)
        return django_file

    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)

    if image.width > max_dimension or image.height > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = io.BytesIO()
    original_name = getattr(django_file, "name", "photo")
    stem = original_name.rsplit(".", 1)[0] if "." in original_name else original_name

    if has_alpha:
        image = image.convert("RGBA")
        image.save(buffer, format="PNG", optimize=True)
        new_name = f"{stem}.png"
    else:
        image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        new_name = f"{stem}.jpg"

    buffer.seek(0)
    return ContentFile(buffer.read(), name=new_name)

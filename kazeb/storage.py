"""
Storage backends for KazeB media files.

SupabasePublicStorage extends FileSystemStorage but overrides url() to
return Supabase Storage public URLs instead of local /media/ paths.
This lets browsers on any origin (including phones on the LAN) fetch
images directly from Supabase Storage without needing S3 credentials
for read access to a public bucket.

Files are still written locally via FileSystemStorage (useful for
development), but the public URL points at Supabase where the same
objects exist from production uploads.
"""

import os

from django.core.files.storage import FileSystemStorage


class SupabasePublicStorage(FileSystemStorage):
    """
    Returns Supabase Storage public URLs for media files.

    Requires KAZEB_EXPECTED_SUPABASE_PROJECT_REF and
    SUPABASE_STORAGE_BUCKET environment variables. Neither is a secret
    (they identify the project and bucket, not access credentials).
    """

    def url(self, name):
        project_ref = os.environ.get("KAZEB_EXPECTED_SUPABASE_PROJECT_REF")
        bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "media")
        if project_ref:
            clean_name = name.lstrip("/")
            return (
                f"https://{project_ref}.supabase.co/"
                f"storage/v1/object/public/{bucket}/{clean_name}"
            )
        return super().url(name)

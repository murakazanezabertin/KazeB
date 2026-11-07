
"""
Downloads Bootstrap's CSS and JS once and saves them under
static/vendor/bootstrap/, so the site never depends on a CDN at runtime.
"""

import base64
import hashlib
import re
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BOOTSTRAP_VERSION = "5.3.3"

CDN_BASE = (
    f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/dist"
)

ASSETS = {
    "bootstrap.min.css": {
        "url": f"{CDN_BASE}/css/bootstrap.min.css",
        "sha384": "QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH",
    },
    "bootstrap.bundle.min.js": {
        "url": f"{CDN_BASE}/js/bootstrap.bundle.min.js",
        "sha384": "YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",
    },
}

VENDOR_DIR = settings.BASE_DIR / "static" / "vendor" / "bootstrap"


class Command(BaseCommand):
    help = "Downloads and prepares local Bootstrap assets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download and overwrite existing files.",
        )

    def handle(self, *args, **options):
        VENDOR_DIR.mkdir(parents=True, exist_ok=True)

        # Download Bootstrap assets and verify their integrity.
        for filename, meta in ASSETS.items():
            dest = VENDOR_DIR / filename

            if dest.exists() and not options["force"]:
                self.stdout.write(
                    f"Skipping {filename} "
                    "(already present, use --force to re-download)."
                )
                continue

            self.stdout.write(
                f"Downloading {filename} from {meta['url']} ..."
            )

            try:
                with urllib.request.urlopen(
                    meta["url"], timeout=15
                ) as response:
                    content = response.read()

            except (urllib.error.URLError, TimeoutError) as exc:
                raise CommandError(
                    f"Could not download {filename}: {exc}\n"
                    "Check your internet connection and try again."
                ) from exc

            digest = hashlib.sha384(content).digest()
            actual_hash = base64.b64encode(digest).decode()
            expected_hash = meta["sha384"]

            if actual_hash != expected_hash:
                raise CommandError(
                    f"{filename} failed integrity check!\n"
                    f"Expected: {expected_hash}\n"
                    f"Received: {actual_hash}\n"
                    "Refusing to save the file."
                )

            dest.write_bytes(content)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Saved {dest} "
                    f"({len(content):,} bytes, integrity verified)."
                )
            )

        # Remove optional source-map references.
        # These map files are not needed for production.
        assets_to_clean = {
            "bootstrap.min.css": (
                rb"/\*[#@]\s*sourceMappingURL=.*?\*/\s*$"
            ),
            "bootstrap.bundle.min.js": (
                rb"(?m)^\s*//#\s*sourceMappingURL=.*?(?:\r?\n|$)"
            ),
        }

        for filename, pattern in assets_to_clean.items():
            file_path = VENDOR_DIR / filename

            if not file_path.exists():
                raise CommandError(
                    f"Bootstrap asset is missing: {filename}"
                )

            original_content = file_path.read_bytes()

            cleaned_content = re.sub(
                pattern,
                b"",
                original_content,
                flags=re.DOTALL if filename.endswith(".css") else 0,
            )

            if cleaned_content != original_content:
                file_path.write_bytes(cleaned_content)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed optional source-map reference "
                        f"from {filename}."
                    )
                )
            else:
                self.stdout.write(
                    f"No source-map reference found in {filename}."
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\nDone. Bootstrap assets are ready for collectstatic."
            )
        )

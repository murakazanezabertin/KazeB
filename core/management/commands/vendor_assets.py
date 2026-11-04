
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
CDN_BASE = f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/dist"

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

        for filename, meta in ASSETS.items():
            dest = VENDOR_DIR / filename

            if dest.exists() and not options["force"]:
                self.stdout.write(
                    f"Skipping {filename} (already present, use --force to re-download)."
                )
                continue

            self.stdout.write(f"Downloading {filename} from {meta['url']} ...")

            try:
                with urllib.request.urlopen(meta["url"], timeout=15) as response:
                    content = response.read()
            except (urllib.error.URLError, TimeoutError) as exc:
                raise CommandError(
                    f"Could not download {filename}: {exc}\n"
                    "Check your internet connection and try again."
                )

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
                    f"Saved {dest} ({len(content):,} bytes, integrity verified)."
                )
            )

        # Remove the optional source-map comment from Bootstrap CSS.
        # WhiteNoise otherwise tries to collect the missing .map file.
        css_path = VENDOR_DIR / "bootstrap.min.css"

        if not css_path.exists():
            raise CommandError("Bootstrap CSS file is missing.")

        css_content = css_path.read_text(encoding="utf-8")

        cleaned_css = re.sub(
            r"/\*[#@]\s*sourceMappingURL=[^*]*\*/\s*$",
            "",
            css_content,
        ).rstrip() + "\n"

        if cleaned_css != css_content:
            css_path.write_text(cleaned_css, encoding="utf-8")
            self.stdout.write(
                self.style.SUCCESS("Removed optional Bootstrap CSS source-map reference.")
            )
        else:
            self.stdout.write("No Bootstrap CSS source-map reference found.")

        self.stdout.write(
            self.style.SUCCESS(
                "\nDone. Bootstrap assets are ready for collectstatic."
            )
        )

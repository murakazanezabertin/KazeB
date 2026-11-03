"""
Downloads Bootstrap's CSS and JS once and saves them under
static/vendor/, so the site never depends on cdn.jsdelivr.net (or any
other CDN) being reachable -- not in local development, not in
production.

Why this exists
----------------
Templates used to load Bootstrap straight from a CDN:

    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">

That's an invisible dependency on outside internet access. If the
machine running the dev server (or, worse, a production host) can't
reach cdn.jsdelivr.net -- a restricted network, a firewall, jsDelivr
being blocked or down in that country, a fully offline demo -- the
browser silently gets no stylesheet at all. Django, the view, and the
template are all completely fine; the page just renders with zero
styling, which looks like the whole site is broken.

Given KazeB's whole point is working reliably in Rwanda (bandwidth and
connectivity vary a lot more there than on a developer's home
broadband), the right fix is to not have that dependency at runtime at
all: fetch the files ONE TIME (this command), commit or bake them into
the image, and serve them like any other static file from then on.

Usage
-----
Run this once, whenever you're on a machine with normal internet
access:

    python manage.py vendor_assets

It downloads bootstrap.min.css and bootstrap.bundle.min.js into
static/vendor/bootstrap/, verifies each against its official sha384
integrity hash (the same hashes getbootstrap.com publishes for its own
CDN links) so a corrupted or tampered download is caught immediately
instead of shipping broken/unsafe CSS, and exits with an error
(without writing anything) if a hash doesn't match.

This also runs automatically during the Docker image build (see
Dockerfile), so a deployed container never needs internet access for
this at all -- the files are already baked in by the time it starts
serving traffic.
"""

import hashlib
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BOOTSTRAP_VERSION = "5.3.3"
CDN_BASE = f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/dist"

# sha384 integrity hashes as published by getbootstrap.com for this
# exact version -- https://getbootstrap.com/docs/5.3/getting-started/introduction/
# Checked against the download, not just used to decorate a <link> tag,
# so a corrupted or substituted file is caught before it's ever served.
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
    help = (
        "Downloads Bootstrap's CSS/JS once and saves them under "
        "static/vendor/bootstrap/, so the site can serve them without "
        "ever depending on a CDN at runtime. Run this whenever you're "
        "on a connection with normal internet access; the Docker build "
        "also runs it automatically."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download and overwrite files that are already present.",
        )

    def handle(self, *args, **options):
        VENDOR_DIR.mkdir(parents=True, exist_ok=True)

        for filename, meta in ASSETS.items():
            dest = VENDOR_DIR / filename

            if dest.exists() and not options["force"]:
                self.stdout.write(f"Skipping {filename} (already present, use --force to re-download).")
                continue

            self.stdout.write(f"Downloading {filename} from {meta['url']} ...")
            try:
                with urllib.request.urlopen(meta["url"], timeout=15) as response:
                    content = response.read()
            except (urllib.error.URLError, TimeoutError) as exc:
                raise CommandError(
                    f"Could not download {filename}: {exc}\n"
                    "This machine may not have internet access right now -- "
                    "run this command again from one that does. Nothing was "
                    "overwritten."
                )

            digest = hashlib.sha384(content).digest()
            import base64

            actual_hash = base64.b64encode(digest).decode()
            expected_hash = meta["sha384"]
            if actual_hash != expected_hash:
                raise CommandError(
                    f"{filename} failed integrity check!\n"
                    f"  expected sha384: {expected_hash}\n"
                    f"  got sha384:      {actual_hash}\n"
                    "Refusing to save a file that doesn't match the official "
                    "release -- this could mean a corrupted download or a "
                    "compromised network. Nothing was written."
                )

            dest.write_bytes(content)
            self.stdout.write(self.style.SUCCESS(f"Saved {dest} ({len(content):,} bytes, integrity verified)."))

        self.stdout.write(self.style.SUCCESS(
            "\nDone. Bootstrap is now served locally from static/vendor/bootstrap/ -- "
            "no CDN needed at runtime. Remember to run 'python manage.py collectstatic' "
            "before deploying if you're not already doing that as part of your build."
        ))

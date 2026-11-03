"""
Vercel entrypoint.

Vercel's Python runtime looks for a WSGI-callable named `app` in
whichever file vercel.json points at. Django's own wsgi.py exposes
`application` (the standard Django name), so this file just imports
it and re-exports it under the name Vercel expects -- it does not
duplicate any app logic.
"""

import os
import sys
from pathlib import Path

# Make the project root (one level up from /api) importable, since
# Vercel runs this file from inside the api/ folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kazeb.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()

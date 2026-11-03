# Fly.io builds and runs this image directly (via `fly launch`/`fly deploy`).
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr,
# so `fly logs` shows output immediately.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System packages needed to build psycopg2 and Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fetch Bootstrap's CSS/JS once, here at build time (this stage always
# has internet access even when the deployed container won't), so the
# running app never depends on a CDN -- see
# core/management/commands/vendor_assets.py for the full reasoning.
# --force means "always re-fetch during a build" rather than trusting
# whatever the image's build context happened to have on disk already.
RUN python manage.py vendor_assets --force

# Gather CSS/JS into STATIC_ROOT so WhiteNoise can serve them. A dummy
# SECRET_KEY is enough for this build-time step -- it never touches
# the database and the real one is supplied at runtime via Fly secrets.
RUN DJANGO_SECRET_KEY=build-time-only-not-used-at-runtime \
    python manage.py collectstatic --noinput

# Fly.io routes traffic to whatever port fly.toml's internal_port says;
# 8080 is used here and matches fly.toml.
EXPOSE 8080

CMD ["gunicorn", "kazeb.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2"]

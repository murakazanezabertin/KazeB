# Deploying to Vercel

Vercel runs Django as a serverless function (via `api/index.py`), not
a long-lived `gunicorn` process like Fly.io/Railway/Render. The
`pyproject.toml` build command prepares the React administrator bundle,
vendored assets, and Django static files before the function is packaged.

Read this in full before your first deploy. Vercel runs the configured
build command on each deployment; migrations and administrator role
assignment remain manual.

## Honest heads-up before you start

Vercel is built for frontend apps and short-lived functions, not
traditional server apps like Django. It will work for KazeB, but:

- **No persistent filesystem.** SQLite and local media storage won't
  work at all -- you MUST set `DATABASE_URL` (Postgres) and the
  `SUPABASE_STORAGE_*` variables (see README's "Media storage"
  section). Both are already wired into `kazeb/settings.py`.
- **Execution time limit.** Free (Hobby) plan functions time out at
  10 seconds. Normal page loads are fine; don't add anything
  slow (e.g. large unoptimized image processing) to a request.
- **Cold starts.** The first request after idle time will be slower
  (~1-2s) while the function spins up.
- Given you've had friction with a previous host already, Railway or
  Render (both run Django the "normal" way, no code changes needed)
  are worth keeping in mind as a fallback if Vercel's constraints
  become annoying.

## One-time local setup (needs real internet access)

The Vercel build command performs these steps. To reproduce them locally,
run them from the project root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build

# Downloads Bootstrap CSS/JS into static/vendor/ if not present.
python manage.py vendor_assets

python manage.py collectstatic --noinput
```

The Bootstrap assets under `static/vendor/` are committed. The Vite bundle
under `static/react/` and collected files under `staticfiles/` are generated
by the build and should not be committed.

## Vercel project setup

1. Push this project to a GitHub/GitLab/Bitbucket repo.
2. In Vercel: **Add New → Project**, import that repo. Vercel will
   detect `vercel.json` and use it automatically -- no framework
   preset needed.
3. **Environment Variables** (Project Settings → Environment
   Variables) -- set at minimum:
   ```
   DJANGO_SECRET_KEY=<generate with the command in settings.py's comment>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=<your-project>.vercel.app,kazeb.rw
   DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-project>.vercel.app,https://kazeb.rw
   DATABASE_URL=<your managed Postgres URL>
   SUPABASE_STORAGE_BUCKET=media
   SUPABASE_STORAGE_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
   SUPABASE_STORAGE_REGION=<your Supabase region>
   SUPABASE_STORAGE_ACCESS_KEY_ID=<...>
   SUPABASE_STORAGE_SECRET_ACCESS_KEY=<...>
   EMAIL_HOST=<your SMTP provider>
   EMAIL_HOST_USER=<...>
   EMAIL_HOST_PASSWORD=<...>
   ```
   (See README's "Launch checklist" for what each optional variable
   does.)
4. Deploy.

## Migrations (every time your models change)

Vercel has no `release` phase (unlike the `Procfile`'s `release:` line
used on Fly/Heroku-style hosts). Run migrations yourself, from your
own machine, pointed at the production database:

```bash
DATABASE_URL=<your production DATABASE_URL> python manage.py migrate
```

Then re-run your `python manage.py seed_categories` (or whichever seed
commands you use) the same way, against that same `DATABASE_URL`, so
production actually has data.

After applying the administrator migrations, run
`python manage.py setup_admin_roles` against that environment and assign
staff accounts to the limited groups through Django admin. This does not
create superusers. Do not run these commands against production without
review and explicit approval.

## What changed in this project for Vercel

- `api/index.py` -- new. Wraps `kazeb.wsgi.application` as `app`,
  which is what Vercel's Python runtime looks for.
- `vercel.json` -- new. Routes every request to `api/index.py` and
  bundles the whole project (templates, static, locale) into the
  function.
- `.vercelignore` -- new. Excludes `db.sqlite3`, local `media/`
  uploads, and the Fly.io-specific `Dockerfile`/`Procfile` from the
  deployment.
- The Vercel build produces the React administrator app in
  `static/react/`; Django serves it at `/admin-dashboard/`. Other
  production pages continue using Django templates.
- Nothing in `kazeb/settings.py`, `Dockerfile`, or `Procfile` was
  changed or removed -- Fly.io deployment still works exactly as
  before if you ever want to switch back or run both.

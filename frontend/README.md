# KazeB React frontend

This Vite app powers the administrator dashboard at `/admin-dashboard/` in
production. The migrated homepage, marketplace, account, and seller pages remain
a development preview; the existing Django pages continue to serve them.

## Run locally

1. Start Django from the repository root:

   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```

2. In another terminal, start Vite:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open the URL Vite prints (by default, `http://127.0.0.1:5173`). Set
`DJANGO_URL` in the frontend environment if Django is listening at a different
address.

Vite proxies the homepage API, existing Django page routes, media, and static
assets to Django. Keeping browser requests on the Vite origin allows the
existing Django session cookie to be used without adding CORS configuration.
The proxy preserves the browser `Host` and `Origin`, so Django's normal
same-origin CSRF checks continue to apply.

## Backend integration

`GET /api/home/` returns categories, the eight most recent active listings,
the existing session's authentication state, and translated homepage and
marketplace labels. `GET /api/listings/` provides active listing search,
category/location/condition filters, existing date/view/price sorting, and
12-item pagination. `GET /api/listings/<id>/` returns an active listing's
details and increments its view count for non-owners, matching the Django
detail view. The React seller page calls the existing
`GET /api/sellers/<username>/` endpoint; its public contact fields are additive.

These endpoints read existing Django models and storage URLs. Seller
management uses `GET /api/seller/dashboard/`, `GET`/`POST /api/seller/listings/`,
`GET`/`PATCH`/`DELETE /api/seller/listings/<id>/`, and
`PATCH /api/seller/listings/<id>/status/`. All listing writes remain in Django, including validation, ownership checks,
database operations, image compression, and storage cleanup. Account and
favorites pages also call Django's existing session-authenticated APIs.

The administrator app uses the permission-protected `/api/admin/` endpoints
for real user, listing, report, review, phone-verification, activity, and
overview data. Django checks `is_staff` plus the relevant model permission on
every API request; opening the React route alone does not grant access.

In the Vite preview, `/listings/search/`, `/listings/category/<slug>/`,
`/listings/<id>/`, `/listings/dashboard/`, `/listings/add/`,
`/listings/<id>/edit/`, `/listings/favorites/`, account pages, and
`/seller/<username>/` are React pages. Messaging, reporting, legacy delete
pages, and other non-migrated pages continue to use Django. Existing Django
templates and production public routes remain intact.

The seller endpoints use Django session authentication. `GET /api/csrf/` issues
Django's CSRF cookie and returns a token. The frontend API client sends that
token as `X-CSRFToken` on non-safe API requests. Django retains the existing
session and CSRF protections for all seller actions.

## Production status

Vercel builds the React assets into `static/react/`, runs `collectstatic`, and
serves the dashboard shell through Django/WhiteNoise. This integration is
limited to `/admin-dashboard/`; it does not switch the homepage or other
production routes away from their Django templates.

The current full development dependency audit reports an upstream high-severity
`picomatch` advisory through Vite's development dependency tree; no patched
`picomatch` release is available yet. `npm audit --omit=dev` reports no
production dependency vulnerabilities. Keep the Vite server bound to localhost
and recheck the full audit before exposing it or upgrading the toolchain.

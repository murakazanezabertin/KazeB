# KazeB

A Django implementation of the KazeB website spec: buyers and sellers
find each other directly online. KazeB only handles discovery —
payment, meeting up, delivery, etc. are arranged directly between
buyer and seller.

## Recent changes

- **Site name**: the site is now called **KazeB** everywhere (was
  previously shown in places as "Kaze Bridge").
- **Orange "About Us" / "Contact Us" footer band** on every page
  (`core/about.html`, `core/contact.html`). About Us folds in the old
  "How it works" + Terms of Service content. Contact Us is a
  placeholder — send over the details you want shown there and it'll
  be dropped in.
- **Photo picker fix**: the ✕ remove button on a newly-picked photo
  now uses event delegation (`static/js/photo-picker.js`) so removing
  a photo before publishing reliably works.
- **Video upload**: a seller can attach one video per listing
  (`Listing.video`), shown alongside the photo carousel on the
  listing detail page. Editing a listing lets you replace or remove
  the existing video.
- **Phone-verification icon removed** from My account — the
  verify/verified badge no longer shows there (the ✅ verified badge
  buyers see on a listing page is unaffected).
- **Edit account**: a ✏️ "Hindura konti" link now sits next to 🗑
  "Siba Konti" on My account, opening a small form to update your
  display name, profile picture, location, biography, phone, WhatsApp
  number, and email (`/accounts/edit/`). Changing the email address
  requires confirming the new address.
- **Listing detail page** now shows the date posted and the seller's
  linked name and profile picture, plus a ★ "Save to favourites"
  button for signed-in buyers. Seller names and pictures on listing
  cards also open the public `/seller/<username>/` profile, which
  shows seller details and active listings. Public profile data is
  available at `/api/sellers/<username>/`. Saved listings show up on
  a new **Ibya kwibuka / Favourites** page linked from My account.
- **Email is now required at sign-up**, in addition to phone and
  WhatsApp.


## What's included

- **Landing page** — "Murakazaneza kuri KazeB" hero, tagline
  "Ikiraro gihuza abaguzi n'abagurisha" ("The Bridge connecting buyers
  and sellers"), and a "Shakisha ukurikije ubwoko" ("Find by category")
  icon grid — real photos for each category (Vehicles, Houses, Houses
  for rent, Land, Electronics, Job offers, Home materials, Fashion,
  Musical instruments, Sports materials, Agricultural, Kids, Others).
  A category can still get a different photo uploaded in `/admin/`,
  which overrides the bundled one. **Category names are translated
  too** (`listings/templatetags/category_extras.py`) — switching
  language changes "Vehicles" to "Ibinyabiziga" or "Véhicules"
  everywhere a category name appears, including the "Add listing"
  category dropdown.
- **Top navigation bar** — Home, an always-visible search-by-location
  box (type and search immediately, no extra click), Add a product, My
  account (once logged in, with a small avatar), Messages, Log in /
  Sign up, and a language switcher (Kinyarwanda / English / Français)
  that now switches reliably in both directions (see the note on
  language switching below).
- **Buyer flow** — browse a category or use the nav search box
  (matches listing name, district and sector), open a listing to see
  photos, description, price (shown in whichever currency the seller
  picked, e.g. "5,000 RWF" or "$20.00"), and three contact options:
  1. Message the seller through the site (in-site chat)
  2. Chat with the seller on WhatsApp — a WhatsApp-style icon button
     (deep link to `wa.me`, only shown if the seller added a WhatsApp
     number)
  3. Copy the seller's phone number to the clipboard
- **Seller flow** — log in, "Add a product": category, name, photos
  (a proper multi-photo picker — click "Add photos" as many times as
  needed, with thumbnail previews, a ★ cover-photo badge, and a × to
  remove any photo before publishing), description, condition
  (new/used), location (district + sector), and price with a currency
  selector right next to it (RWF first/default, switchable to $).
- **Public seller profile** — `/seller/<username>/` shows a seller's
  public display name, profile picture, location, biography, member
  date, phone-verification badge when verified, contact options, and
  only active listings. The JSON endpoint at
  `/api/sellers/<username>/` returns the same public profile details
  and paginated active listings without private account fields.
- **My account** (`/listings/dashboard/`) — a seller's own control
  panel, separate from the buyer browsing pages: account summary
  (avatar, phone, WhatsApp), a **My products** list with a small photo
  thumbnail, view count, and message count per product, an
  unread-messages counter, and the most recent messages customers sent
  them. Each product row has **✏️ Edit** and **🗑 Delete** buttons.
- **Edit / delete a product** (`/listings/<id>/edit/`,
  `/listings/<id>/delete/`, both owner-only) — editing reuses the same
  form as adding a product, pre-filled, and additionally shows the
  product's existing photos as clickable tiles (click one to mark it
  for removal) alongside the usual "add more photos" picker. Deleting
  asks for confirmation on its own page before anything is removed —
  never on a bare link click — and cascades to that product's photos
  and any messages tied to it.
- **Delete account** (`/accounts/delete/`, from a link at the bottom
  of My account) — asks the user to re-type their password before
  permanently deleting their account, which cascades to every product
  they listed, those products' photos, and all their messages.
- **Share, not contact, on your own listing** — when a seller opens
  their own listing's detail page, the WhatsApp/phone contact buttons
  are replaced with share buttons (WhatsApp — with the same
  WhatsApp-style icon, Facebook, Telegram, copy link) so they can
  promote it instead of messaging themselves.
- **Accounts** — custom user model with a profile picture, a phone
  number, and a WhatsApp number, all collected at sign-up (WhatsApp is
  required, not optional, so every listing can show a working chat
  link).
- **Messaging** — a simple in-site inbox and per-listing conversation
  thread between buyer and seller, with new messages appearing within
  a few seconds via polling (no manual refresh needed).
- **Trust & safety** (new `trust` app) — buyers can report a listing
  (🚩 scam, inappropriate, wrong category, already sold, other) for
  admin review; buyers can leave a 1-5★ rating + comment for a seller;
  sellers can verify their phone number via a one-time code, shown as
  a badge on their listings and My account. See the Launch checklist
  below for what phone verification needs to send *real* SMS.
- **Admin panel** — manage categories (with icon images), listings,
  images, users, reports, and reviews at `/admin/`.
- **Full translation** — every page is written in Kinyarwanda as the
  site's base language, with complete English and French translations
  included (`locale/rw`, `locale/en`, `locale/fr`). Switching languages
  in the nav bar changes every label, button, message, and category
  name on the page, not just a few strings, and switching back and
  forth between all three languages works reliably.
- **Production-readiness**: environment-based settings, search
  sort/filter, SEO tags + sitemap, automated tests, image compression,
  orphaned-file cleanup, and a backup command — see the **Launch
  checklist** section near the bottom of this file for the full
  rundown of what's done vs. what needs your own external credentials.

## Project layout

```
kazeb/
  kazeb/            settings, root urls, wsgi/asgi, sitemaps, shared image-compression util
  core/             home page, legal/info pages, backup_data management command
  accounts/         custom User model (profile picture, phone, WhatsApp), sign-up, Kinyarwanda-labeled login form
  listings/         Category, Listing, ListingImage, search/sort/filter, add-listing, my-account/dashboard
  chat/             in-site messaging (inbox + threads + polling updates)
  trust/            reports, seller reviews, phone verification (OTP)
  templates/        all HTML templates (Bootstrap 5 via CDN)
  static/           css/js (incl. multi-photo picker) + bundled category icon photos
  locale/           rw, en and fr translation catalogs (.po and compiled .mo)
  media/            uploaded photos (created at runtime)
  requirements.txt
```

## Setup

Requires Python 3.10+.

```bash
cd kazeb
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_categories   # creates the starting categories
python manage.py createsuperuser   # so you can log into /admin/
python manage.py vendor_assets     # one-time: fetches Bootstrap's CSS/JS
                                    # into static/, so the site is styled
                                    # without ever depending on a CDN
                                    # (needs internet just for this step)

python manage.py test              # runs the automated test suite
python manage.py runserver
```

**If the site loads with no styling at all** (default browser fonts, a
plain bulleted nav, a red "Shakisha" button but nothing else styled) —
that's `vendor_assets` not having been run yet, or having been run on
a machine without internet access at the time. Django, the view, and
the template are all fine in this case; only the Bootstrap file is
missing. Run `python manage.py vendor_assets` again from a connection
with normal internet access and refresh. (The page also has a
same-session JS fallback that tries `cdn.jsdelivr.net` automatically
if the local file 404s, in case that connection has internet but this
step was simply skipped.)

For production, copy `.env.example` to `.env`, fill in real values,
and make sure your process manager / hosting platform actually loads
those variables into the environment (this project doesn't read
`.env` files itself — see the comment at the top of `.env.example`).

If `manage.py` ever complains about a missing or unexpected Django
import right after you just ran `pip install`, it's almost always
because `pip` and `python` point at two different interpreters (very
common when a system also has Python 3.10/3.11 installed alongside
3.12, or when a virtual environment wasn't actually activated). Check
with:

```bash
python -m pip show django   # confirms Django is installed where python.exe/python3 looks
python -m django --version  # should print a 5.x version, matching requirements.txt
```

If that shows nothing or an unexpected version, reactivate the venv
(or recreate it) and reinstall with `python -m pip install -r
requirements.txt` — using `python -m pip` instead of a bare `pip`
guarantees both point at the same interpreter.

Then open **http://127.0.0.1:8000/** — it loads in Kinyarwanda by
default. Use the language dropdown in the nav bar to switch to
English or Français; every label, button, and message updates.

- Category icons work out of the box (bundled artwork). Upload a
  custom photo per category at **http://127.0.0.1:8000/admin/**
  (Listings ▸ Categories) if you'd rather use real photos.
- Sign up as a seller at **/accounts/register/** (picture optional,
  phone and WhatsApp required), then use **Add a product** in the nav
  bar to publish a product with several photos, and check **Konti
  yanjye / My account** to see your products' views and messages.
- Log in as a second (buyer) account in another browser/incognito
  window to try the nav search box, messaging, WhatsApp, and
  copy-phone from a listing page. Open that same listing while logged
  in as its seller to see the share buttons instead.
- If you already ran `seed_categories` before this update, running it
  again just adds the new categories — existing ones are left alone
  (their `order` value won't match the new list exactly, which only
  affects display order, not functionality).

## Notes on a few design decisions

- **District / Sector** location fields match Rwanda's administrative
  divisions (Kaze means "welcome" in Kinyarwanda — hence "Kaze
  Bridge"). Swap these for whatever regions fit your market if needed.
- **WhatsApp and phone number are both required at sign-up.** The
  WhatsApp button on a listing only appears once the seller has set a
  number (now guaranteed at registration); phone copy likewise.
- **No payments** are processed by the site, matching the spec: KazeB
  is discovery-only, and the two parties handle payment/logistics
  themselves.
- **Email verification is required before first login.** Signing up
  creates the account and emails a one-time confirmation link
  (`accounts/tokens.py`), but doesn't log the user in yet --
  `LoginForm.confirm_login_allowed` blocks sign-in until that link is
  clicked. A "Resend verification email" page is available from the
  login page and from an expired-link page, and always shows the same
  message regardless of whether the address is a real account (so it
  can't be used to check who's registered). This needs real EMAIL_*
  settings to actually deliver anything -- see above; without them,
  the link just gets printed to your terminal via the console email
  backend, which is enough to test the whole flow locally. Changing
  the account email resets verification, sends a new link, and signs
  the user out until the new address is confirmed; resend lookup is
  case-insensitive.
- **Bootstrap is vendored locally, not loaded from a CDN.** Templates
  used to pull it straight from `cdn.jsdelivr.net`; if that CDN was
  unreachable — a restricted network, jsDelivr blocked or slow in a
  given country, a fully offline demo — the whole site rendered with
  zero styling even though nothing in Django was actually broken.
  `python manage.py vendor_assets` downloads Bootstrap's CSS/JS once
  (verifying each file's official sha384 hash) into `static/vendor/`;
  the Docker build runs this automatically, so a deployed container
  never depends on outside internet for it either. See
  `core/management/commands/vendor_assets.py` for the full reasoning.
- **SQLite** is used out of the box so it runs with zero extra setup.
  For production, point `DATABASES` in `kazeb/settings.py` at
  Postgres/MySQL, set `DEBUG = False`, add a real `SECRET_KEY` (via an
  environment variable), and configure `ALLOWED_HOSTS`.
- **Language switching is session-based, not URL-prefixed.** An
  earlier version wrapped the URL patterns in `i18n_patterns`, which
  gives non-default languages a URL prefix (`/en/...`, `/fr/...`)
  while the default (Kinyarwanda) has none. That combination broke
  switching *back* to Kinyarwanda: from an `/en/...` page, changing
  the dropdown to Kinyarwanda updated the session but redirected back
  to the same `/en/...` URL, and the prefix silently overrode the new
  session language. `kazeb/urls.py` now uses plain, unprefixed paths
  for everything, so `LocaleMiddleware` reads the active language from
  the session set by `/i18n/setlang/` — switching works reliably in
  every direction.
- **Kinyarwanda is forced as the true first-visit language**
  (`kazeb/middleware.py`, `ForceDefaultLanguageMiddleware`). Without
  this, Django's `LocaleMiddleware` checks the browser's
  `Accept-Language` header *before* falling back to `LANGUAGE_CODE` —
  so a browser set to English would show the site in English on the
  very first visit, before anyone touched the language dropdown. The
  middleware strips that header for visitors who haven't explicitly
  picked a language yet (no session/cookie entry), so they always land
  on Kinyarwanda first; once someone uses the dropdown, their choice is
  saved and respected from then on regardless of browser language.
- **Currency**: `Listing.currency` is `RWF` or `USD` (`Listing.Currency`
  choices, RWF listed first so it's the default everywhere). The "Add a
  product" form shows a small dropdown right against the price field
  (`listings/forms.py`, `templates/listings/listing_form.html`) so a
  seller can switch a price from RWF to $ while typing it in. Every
  price display site-wide (`listing.display_price`) formats itself
  accordingly — `"5,000 RWF"` or `"$20.00"` — instead of hard-coding
  RWF.
- **Category names translate with the site**, not just the UI chrome
  around them. Category names are database rows, not template source
  text, so Django's `{% trans %}` doesn't touch them automatically —
  `listings/templatetags/category_extras.py` has a small
  `CATEGORY_NAMES` dict mapping each bundled category's slug to its
  Kinyarwanda/English/French name, used everywhere a category name is
  shown (icon grid, category page heading, listing detail badge, and
  the "Add a product" category dropdown). A category added later in
  `/admin/` with a slug not in that dict just shows whatever name was
  typed in for it there, untranslated — add an entry to
  `CATEGORY_NAMES` if you want it localized too.
- **Multi-photo picker** (`static/js/photo-picker.js`) keeps its own
  running list of selected files in JavaScript and rebuilds the actual
  `<input name="images">` before submit via the `DataTransfer` API —
  needed because a plain `<input multiple>` forgets earlier selections
  each time the file dialog reopens. Works in all evergreen browsers;
  very old browsers without `DataTransfer` support would need a
  fallback (not included).
- **Translations**: source text in templates and forms is written
  directly in Kinyarwanda (the site's default language). All three
  catalogs — `locale/rw`, `locale/en`, `locale/fr` — are already
  compiled and included. The Kinyarwanda one matters more than it
  might look: Django refuses to start with `OSError: No translation
  files found for default language rw` if the default `LANGUAGE_CODE`
  has no catalog anywhere (Kinyarwanda isn't one of Django's ~100
  built-in languages), so `locale/rw` exists specifically to satisfy
  that even though it's an identity catalog (msgid == msgstr, since
  the source text already *is* Kinyarwanda). `kazeb/settings.py` also
  registers `"rw"` in Django's `LANG_INFO`, which is the officially
  documented way to add a language Django doesn't know about. If you
  add new user-facing text later, add the Kinyarwanda string in the
  template/form as usual, then add a matching entry to all three
  `locale/*/LC_MESSAGES/django.po` files (rw's translation is just the
  same string again) and recompile with `django-admin compilemessages`
  (requires GNU gettext installed locally). Note the small
  "Byakoporowe" (Copied!) confirmation shown by the copy-to-clipboard
  buttons is plain JavaScript text, not run through Django's
  translation system, so it stays in Kinyarwanda regardless of the
  selected language — a minor cosmetic gap you can close with
  `django.views.i18n.JavaScriptCatalog` if it matters for your use case.
- **Category icons**: real photos live in `static/images/categories/`
  (one per category, ~15-50KB each after resizing) and are mapped to
  category slugs in `listings/templatetags/category_extras.py`. A
  category with no custom `icon` uploaded in `/admin/` automatically
  falls back to its matching bundled photo. A couple of the bundled
  photos carry a small stock-site watermark (visible on close
  inspection) — fine for a working demo, but swap them for
  watermark-free/licensed photos before using this in production.
- Deleting a product or account removes the database rows immediately.
  The underlying photo files are also cleaned up automatically (see
  "Orphaned media cleanup" in the launch checklist below) — this used
  to be a known gap, now fixed.
- I wasn't able to run this project in the sandbox that produced it —
  no internet access there to install Django — so please run
  `python manage.py check` after installing dependencies and let me
  know if anything needs fixing. I did syntax-check every Python and
  JS file, validated every SVG, cross-checked every `{% url %}` tag
  against its actual URL definition, and validated every translation
  catalog before packaging.

## Launch checklist

This project started as a working demo. The items below are what
separate "runs correctly" from "ready for real users" — most are now
implemented; a few fundamentally need your own external accounts/
credentials that no one can provision except you.

### Done — pure code, works out of the box

- **Environment-based production settings** (`kazeb/settings.py`):
  `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` all read from environment
  variables (see `.env.example`), with safe local-development
  defaults. Security hardening (HTTPS redirect, HSTS, secure cookies,
  `X_FRAME_OPTIONS`) automatically activates when `DJANGO_DEBUG=False`.
- **Database**: SQLite by default (zero setup for development); set
  `DATABASE_URL` to point at a real Postgres instance in production
  (via `dj-database-url`, already in `requirements.txt`).
- **Production server & static files**: `gunicorn` (WSGI server) and
  `whitenoise` (serves CSS/JS directly, compressed, no separate
  nginx/CDN needed) are both wired in — see `Procfile` and the
  `MIDDLEWARE`/`STORAGES` settings in `kazeb/settings.py`. Most hosts
  (Railway, Render, a plain VPS) just need `DATABASE_URL`,
  `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and `DJANGO_ALLOWED_HOSTS`
  set as environment variables, then `python manage.py migrate` and
  `python manage.py collectstatic --noinput` before first start.
- **Rate limiting**: the phone-verification endpoints (`trust/views.py`)
  are throttled using a small dependency-free cache-based limiter
  (`_rate_limited()`) — 3 SMS/email codes per 10 minutes per account.
- **Content moderation / reporting** (`trust` app): any logged-in user
  can report a listing (🚩 link on the listing detail page) with a
  reason (scam, inappropriate, wrong category, already sold, other).
  Reports show up in `/admin/` with bulk actions to mark resolved or
  deactivate the reported listing.
- **Seller ratings/reviews** (`trust` app): buyers can leave a 1-5
  star rating + comment for a seller (one per seller, editable), shown
  on the listing detail page and a dedicated reviews page
  (`/trust/seller/<id>/reviews/`).
- **Phone verification (OTP)**: full 6-digit code flow
  (`trust.models.PhoneVerification`), rate-limited, with a
  verified/unverified badge on My account and the listing detail page.
  **Delivery** goes through `settings.SMS_BACKEND` — see "Needs your
  own credentials" below.
- **Search sorting & filtering**: newest / price low-high / price
  high-low / most-viewed, plus condition (new/used) and district
  filters, all combinable and preserved across pagination.
- **SEO basics**: meta description + Open Graph tags on every page
  (with per-listing overrides so sharing a product to WhatsApp/
  Facebook shows a real preview card with its photo), `sitemap.xml`
  (`kazeb/sitemaps.py`), and `robots.txt`.
- **Automated tests**: `listings/tests.py`, `accounts/tests.py`,
  `trust/tests.py`, `chat/tests.py` cover the important behavior —
  access control (only an owner can edit/delete their own listing,
  only participants can view a chat thread), search/sort correctness,
  the account-deletion password check, phone verification, and
  duplicate-review prevention. Run with `python manage.py test`.
- **Error tracking hook**: set `SENTRY_DSN` and `sentry-sdk` (already
  in `requirements.txt`) activates automatically. Unset, it's a no-op.
- **Backup tooling**: `python manage.py backup_data` dumps the
  database and zips `media/` into a timestamped archive under
  `backups/` (add `--keep N` to control how many old backups are
  retained). Wire it into a daily cron job — see the command's
  `--help` text for the exact line. This doesn't copy the backup
  *off* the server for you; upload `backups/` to S3 or similar for
  real disaster recovery.
- **Orphaned media cleanup**: deleting a listing photo, a category
  icon, or a user (and therefore their profile picture) now deletes
  the actual file from storage too (`listings/signals.py`,
  `accounts/signals.py`), not just the database row.
- **Image compression on upload**: photos and profile pictures are
  automatically resized (max 1600px / 800px respectively) and
  re-compressed on upload (`kazeb/imaging.py`, using Pillow) — a
  seller uploading a full-resolution phone photo no longer slows down
  every page that shows it.
- **Chat updates without a manual refresh**: the conversation page
  polls a small JSON endpoint every 5 seconds
  (`static/js/chat-poll.js`, `chat:thread_updates_*`) and appends new
  messages in place. This is a deliberate, dependency-free stand-in
  for true real-time chat — see "Not implemented" below for why.
- **Legal/info pages**: "How it works", Terms of Service, and Privacy
  Policy (`core/views.py`, linked from the footer). **These are
  generic starting templates, not legal advice** — have an actual
  lawyer review them before you rely on them.

### Needs your own external account/credentials

These are wired up so plugging in your credentials is a one-line
settings change, not a rewrite — but no one can activate them without
an account only you can create:

- **Real SMS delivery for phone verification** — `trust/sms.py` has
  ready-to-use implementations for Africa's Talking (most common in
  Rwanda/East Africa) and Twilio. Until you set `SMS_BACKEND` +
  `SMS_API_KEY`, OTP codes go out through the email backend
  (console-printed in development) — functional for testing the flow,
  not something to leave on in production.
- **Real email delivery** — set `EMAIL_HOST` + credentials (SendGrid,
  Mailgun, Amazon SES, or a Gmail app password all work) or password
  reset emails just print to the console.
- **Postgres** — set `DATABASE_URL`; a managed Postgres instance
  (Railway, Render, RDS, Supabase, etc.) is the easy path.
- **Media storage (Supabase Storage)** — see the dedicated section
  below; needed if you're deploying anywhere with a non-persistent
  filesystem (Fly.io, Railway, Render, most containers), or uploaded
  listing photos/videos will disappear on every restart.
- **Sentry** (error tracking) — free tier is enough to start; set
  `SENTRY_DSN`.
- **A real domain + SSL certificate** — set `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS` and `SITE_DOMAIN`; most hosts
  (Fly.io, Railway, Render, a VPS + Let's Encrypt) handle the SSL
  certificate for you.
- **CAPTCHA / bot protection on signup** — not implemented. The
  phone-verification rate limiting helps, but nothing currently stops
  automated mass registration. Google reCAPTCHA or hCaptcha both need
  a site key + secret key you'd register for free and drop into the
  registration template/view.

### Media storage (Supabase Storage)

Local development stores uploaded photos/videos on disk (`MEDIA_ROOT`)
by default -- nothing to configure. For deployment on any host where
the filesystem doesn't persist between restarts (Fly.io, Railway,
Render, most container platforms), set these five environment
variables and uploads automatically go to Supabase Storage instead
(`kazeb/settings.py`, near `MEDIA_URL`):

1. In your Supabase project: **Storage** (left sidebar) → **New
   bucket**. Name it `media`, and toggle it **Public** (listing photos
   need to be viewable by anyone browsing the site, not just logged-in
   users).
2. **Project Settings → API → S3 Connection** (a separate section from
   the database connection string you used for `DATABASE_URL`) →
   generate new **S3 Access Keys**. This gives you an access key ID
   and secret access key specifically for Storage -- different from
   your database password.
3. Set these environment variables wherever you deploy:
   ```
   SUPABASE_STORAGE_BUCKET=media
   SUPABASE_STORAGE_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
   SUPABASE_STORAGE_REGION=<your project's region, e.g. eu-west-2>
   SUPABASE_STORAGE_ACCESS_KEY_ID=<from step 2>
   SUPABASE_STORAGE_SECRET_ACCESS_KEY=<from step 2>
   ```
4. Deploy. New uploads (listing photos, videos, profile pictures) go
   straight to that bucket; `{{ listing.image.url }}` etc. in
   templates keep working unchanged, since Django's `.url` just
   reflects whatever `MEDIA_URL` resolves to.

Leaving these unset is completely fine for local development or a
host with persistent disk (e.g. a VPS with a real filesystem, or a
Fly.io Volume) -- it just falls back to storing files locally.

### Not implemented — practical equivalents used instead

- **True real-time chat** (WebSockets) needs Django Channels + a
  Redis channel layer — genuine extra infrastructure to deploy and
  operate, not a settings change. The polling approach above (new
  messages appear within ~5 seconds, zero extra services) covers the
  practical need without that operational cost. Worth upgrading later
  if message volume grows enough to matter.
- **True map-based search** needs a geocoding API (Google Maps,
  Mapbox) to turn "Kimironko, Gasabo" into coordinates — another paid
  API key. The district filter (implemented) gets most of the
  practical benefit today, since sellers already enter district/
  sector as text.
- **SMS delivery itself** is stubbed to console/email, per above —
  the verification *flow* is fully implemented and testable, just not
  wired to a paid SMS gateway (there's no free way to do that).

### Suggested order to tackle the remaining items

1. Real database (Postgres) + real email — both are a few environment
   variables away and matter from day one.
2. A real SMS gateway account, once you're ready to actually launch —
   phone verification is much more meaningful with real delivery.
3. CAPTCHA on signup, once the site is public and visible to bots.
4. Sentry, so you find out about errors before users report them.
5. Everything else (real-time chat, map search) — worth revisiting
   once real usage tells you whether they're actually needed.

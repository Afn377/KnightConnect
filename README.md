# KnightConnect

## Contributors

| Name | GitHub Handle | Contribution |
| --- | --- | --- |
| Han Wang | @doublehan2023 | |
| Soraya Mosavi | SorayaM0 | |
| Rushil Pandya | rushil1356 |  |
| S M Afnan Haider | Afn377 | Backend |

## Backend

The backend is a Django + Django REST Framework API in `backend/`, backed by
PostgreSQL (Neon) in deployed environments and SQLite locally by default.

### Local setup

Requires Python 3.12+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
python manage.py runserver
```

Profile pictures are stored in `backend/media/` locally. In production set the
`R2_*` variables from `.env.example` to store them in Cloudflare R2.

`seed_catalog` loads the starter skills, roles, and interests from
`catalog/seed_data.py` and is safe to rerun. To add or update an event:

```bash
python manage.py seed_catalog --event "HackRU Spring 2027" --starts 2027-04-10T10:00:00-04:00 --ends 2027-04-11T14:00:00-04:00
```

The API is served at `http://localhost:8000/api/` (health check at
`/api/health/`) and the admin at `http://localhost:8000/admin/`.

To use PostgreSQL locally or Neon, set `DATABASE_URL` in `backend/.env`.

### Tests

```bash
cd backend
DJANGO_DEBUG=true python manage.py test
```

GitHub Actions runs the suite (and a missing-migration check) on every
push to `main` and `afnan` and on pull requests.

### Scheduled jobs

Opportunities past their expiry and accounts past their 3-day recovery
period need a periodic job. Either:

- call `GET /api/internal/maintenance/` with `Authorization: Bearer $CRON_SECRET`
  (Vercel Cron sends this header automatically when `CRON_SECRET` is set), or
- run `python manage.py expire_opportunities` from any scheduler to handle
  expiry alone.

Running it hourly is enough for the pilot.

### API

All endpoints live under `/api/`. The frontend authenticates with Django's
session cookie: call `GET /api/auth/csrf/` first and send the returned token
as the `X-CSRFToken` header on every `POST`, `PATCH`, and `DELETE`. Endpoints
require a signed-in user unless noted. Errors use DRF's format
(`{"detail": ...}` or `{"field": ["message"]}`), with 401 when signed out,
403 when not allowed, 404 for anything hidden from the user, 409 for state
conflicts, and 429 when rate limited.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health/` | Liveness and database check (public) |
| GET | `/auth/csrf/` | Set the CSRF cookie (public) |
| POST | `/auth/request-code/` | Email a 6-digit sign-in code to a Rutgers address (public) |
| POST | `/auth/verify-code/` | Sign in with the code; creates the account or restores one pending deletion (public) |
| POST | `/auth/logout/` | Sign out |
| GET, PATCH | `/me/` | Own profile, including major, year, interested events and availability for each |
| POST, DELETE | `/me/avatar/` | Upload (multipart `image`) or remove the profile picture |
| DELETE | `/me/` | Schedule account deletion after a 3-day recovery period |
| GET, POST | `/me/contact-methods/` | List or add contact methods |
| PATCH, DELETE | `/me/contact-methods/{id}/` | Edit or remove a contact method |
| GET | `/users/{id}/` | Another student's public profile |
| GET, POST | `/skills/`, `/roles/`, `/interests/` | Catalog lists (`search`), or add an entry by name (returns the existing one if it matches) |
| GET | `/events/` | Active events that haven't ended, with location and status (`status`) |
| GET, POST | `/opportunities/` | Browse with a `match` for each card (`q`, `event`, `role`, `skill`, `interest`, `type`, `commitment`, `location`, `status`, `sort=best_match\|newest`), or post (`draft: true` saves a draft) |
| GET | `/opportunities/mine/` | Own posts with tab counts (`status=active\|closed\|expired\|draft`) |
| GET, PATCH, DELETE | `/opportunities/{id}/` | View; as the owner, edit or delete |
| POST | `/opportunities/{id}/publish/` | Publish a draft |
| POST | `/opportunities/{id}/close/`, `/reopen/` | Close recruiting early (pending requests stay reviewable) or reopen before the deadline |
| GET | `/opportunities/{id}/team/` | Confirmed team, for the owner and members |
| GET | `/opportunities/{id}/matches/` | Ranked candidates for the owner |
| GET | `/recommendations/` | Ranked opportunities for the signed-in student |
| GET, POST | `/requests/` | List with tab counts (`box`, `status` comma-separated, `opportunity`) or send a join request or invite |
| GET | `/requests/{id}/` | View a request; includes contact details once accepted |
| POST | `/requests/{id}/accept/`, `/decline/`, `/cancel/` | Respond to or withdraw a request |
| POST | `/requests/{id}/feedback/` | Rate whether an accepted connection helped |
| GET, POST | `/blocks/` | List blocked users or block someone |
| DELETE | `/blocks/{user_id}/` | Unblock |
| POST | `/reports/` | Report a user |
| POST | `/analytics/track/` | Record `opportunity_viewed` or `recommendation_viewed` |
| GET | `/analytics/funnel/` | Staff only: funnel counts (`start`, `end` as YYYY-MM-DD) |
| GET, POST | `/internal/maintenance/` | Scheduled housekeeping; requires `Authorization: Bearer $CRON_SECRET` |

### Apps

| App | Responsibility |
| --- | --- |
| `core` | Shared base models, choices, validators, health check |
| `catalog` | Skills, roles, interests, and events |
| `accounts` | Rutgers-only users, profiles, skills, contact methods |
| `opportunities` | Time-limited team postings with open roles and skills |
| `connections` | Join requests, invites, and in-app connection feedback |
| `matching` | Persisted ranked recommendations with explanations |
| `safety` | Blocking and reporting |
| `analytics` | Discovery funnel events |

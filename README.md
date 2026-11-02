# KnightConnect

## Contributors

| Name | GitHub Handle | Contribution |
| --- | --- | --- |
| Han Wang | @doublehan2023 | |
| Soraya Mosavi | SorayaM0 | |
|  |  |  |
|  |  |  |

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
python manage.py createsuperuser
python manage.py runserver
```

The API is served at `http://localhost:8000/api/` (health check at
`/api/health/`) and the admin at `http://localhost:8000/admin/`.

To use PostgreSQL locally or Neon, set `DATABASE_URL` in `backend/.env`.

### Tests

```bash
cd backend
python manage.py test
```

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
| GET, PATCH | `/me/` | Own profile |
| DELETE | `/me/` | Schedule account deletion after a 3-day recovery period |
| GET, POST | `/me/contact-methods/` | List or add contact methods |
| PATCH, DELETE | `/me/contact-methods/{id}/` | Edit or remove a contact method |
| GET | `/users/{id}/` | Another student's public profile |
| GET | `/skills/`, `/roles/`, `/interests/`, `/events/` | Catalog lists |
| GET, POST | `/opportunities/` | Browse (`q`, `event`, `role`, `skill`, `type`) or post an opportunity |
| GET | `/opportunities/mine/` | Own opportunities (`status`) |
| GET, PATCH | `/opportunities/{id}/` | View, or edit as the owner |
| POST | `/opportunities/{id}/close/` | Close early as the owner |
| GET | `/opportunities/{id}/matches/` | Ranked candidates for the owner |
| GET | `/recommendations/` | Ranked opportunities for the signed-in student |
| GET, POST | `/requests/` | List (`box`, `status`) or send a join request or invite |
| GET | `/requests/{id}/` | View a request; includes contact details once accepted |
| POST | `/requests/{id}/accept/`, `/decline/`, `/cancel/` | Respond to or withdraw a request |
| POST | `/requests/{id}/feedback/` | Rate whether an accepted connection helped |
| GET, POST | `/blocks/` | List blocked users or block someone |
| DELETE | `/blocks/{user_id}/` | Unblock |
| POST | `/reports/` | Report a user |
| POST | `/analytics/track/` | Record `opportunity_viewed` or `recommendation_viewed` |
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

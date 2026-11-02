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

# Kepler Student Guild Voting System

An online voting platform for the Kepler College (Kigali, Rwanda) student guild elections, built with Django.

## Features

**Students**
- Sign up with email + student ID (both unique), verify by email, log in with either
- Browse elections, candidates and campaign posts
- Apply to run for open positions (admin-defined application questions)
- Approved candidates publish campaign posts (moderated)
- Vote once per position; results shown after close (or live, if enabled)
- Winners submit achievements to the public Guild History

**Admins** (`/dashboard/admin/`)
- Manage elections, positions, application forms and cohorts
- Restrict who can see / vote in an election or position by cohort
- Review applications, campaign posts and achievements
- Verify, block and unblock students; confirm cohorts
- Declare winners, view analytics, export results as CSV or PDF

## Run locally

Needs Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000. With no configuration the app runs in debug mode,
uses SQLite, and prints verification emails to the terminal instead of sending them.

Run the tests:

```bash
python manage.py test
```

## Deploy

The app reads all production settings from environment variables; see
[`.env.example`](.env.example) for the full list.

### Option A — Render (one click)

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, select the repo. `render.yaml` creates the web
   service and a PostgreSQL database and generates `DJANGO_SECRET_KEY`.
3. In the service's **Environment** tab fill in `SITE_URL`, `DJANGO_ADMIN_EMAIL`,
   `DJANGO_ADMIN_PASSWORD` and the `EMAIL_*` values.
4. Deploy. The build runs `build.sh` (install → collectstatic → migrate → create admin).

> **Free-tier limits:** the free database expires after 30 days, the app sleeps
> when idle (first request takes ~1 min), and uploaded photos are lost on each
> redeploy because there is no persistent disk. For the real election use a paid
> instance with a disk mounted at `DJANGO_MEDIA_ROOT`, or move uploads to cloud storage.

### Option B — any other host (Railway, a VPS, PythonAnywhere…)

1. Set the variables from `.env.example`.
2. Run `./build.sh` on each release.
3. Start the app with the command in `Procfile`:
   `gunicorn kepler_voting.wsgi:application`

### Email

Sign-up verification and password reset need a real SMTP account in production.
For Gmail/Google Workspace, use an [app password](https://support.google.com/accounts/answer/185833)
with `EMAIL_HOST=smtp.gmail.com`.

## Project layout

```
kepler_voting/     settings, URLs, WSGI
apps/accounts/     custom user (email + student ID), sign-up, verification, login
apps/elections/    elections, positions, applications, campaigns, voting, results
apps/dashboard/    student dashboard + admin dashboard, analytics, exports
apps/history/      public guild history (past councils + achievements)
apps/core/         home / about pages
templates/, static/
```

## Troubleshooting

**`no such table: accounts_user`** — the local database was created before the
custom user model. Delete `db.sqlite3` and run `python manage.py migrate` again.

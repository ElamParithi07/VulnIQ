# VulnIQ

Personalized Cyber Threat Intelligence SaaS MVP. Ingests NVD/CISA KEV/FIRST EPSS daily, matches
vulnerabilities to each customer's selected product tags, prioritizes with a fixed scoring
formula, generates AI risk summaries via Gemini, and emails a daily digest via Resend.

Product/architecture decisions live in `../plans/` (in particular `VULNIQ_KNOWLEDGE.md` and the
numbered `IMPLEMENTATION_*.md` files) — this README covers running and operating the code.

## Stack

- Django 6.1, PostgreSQL (SQLite for local dev), pytest
- Gemini API (AI enrichment), Resend API (email delivery)
- Gunicorn + WhiteNoise for production serving

## Local setup

```bash
python -m venv .venv
.venv/Scripts/activate  # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env    # then fill in GEMINI_API_KEY / RESEND_API_KEY if you need real sends
python manage.py migrate
python manage.py seed_taxonomy
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` — redirects to the dashboard (signup/login required),
`/admin/` for the operator console.

## Tests

```bash
pytest
```

209 tests across all apps, including `tests/test_end_to_end.py` which chains signup → verify →
tag selection → digest enable, and ingestion → matching → scoring → snapshot → AI enrichment →
email send, through their real entrypoints. No test depends on a live external API — NVD, KEV,
EPSS, Gemini, and Resend are all dependency-injected and stubbed in tests.

## Running the pipeline manually

```bash
python manage.py run_daily_pipeline            # scheduled run
python manage.py run_daily_pipeline --backfill # marks the run as a manual backfill
```

This is the single canonical pipeline entrypoint — the admin "Run daily pipeline now" button and
the `/internal/trigger-pipeline/` HTTP endpoint both call the exact same underlying function
(`ingestion.services.daily_pipeline.run_daily_digest_pipeline`), protected by a DB-backed lock so
overlapping runs can't happen.

## Key environment variables

See `.env.example` for the full list. Notable ones:

| Variable | Purpose |
|---|---|
| `USE_SQLITE` | `true` for local dev; `false` to use the `POSTGRES_*` vars |
| `GEMINI_API_KEY` / `GEMINI_MODEL_NAME` | AI enrichment |
| `RESEND_API_KEY` / `DEFAULT_FROM_EMAIL` | Email delivery — `DEFAULT_FROM_EMAIL` must be on a domain verified in Resend for production sends |
| `PIPELINE_TRIGGER_TOKEN` | Shared secret required by `/internal/trigger-pipeline/` |

## Deployment (Render free tier + cron-job.org)

1. Set env vars above on the Render web service (`DJANGO_DEBUG=false`, real `DJANGO_SECRET_KEY`,
   `DJANGO_ALLOWED_HOSTS`, `USE_SQLITE=false` + Postgres vars, API keys, `PIPELINE_TRIGGER_TOKEN`).
2. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
3. Start command: `gunicorn config.wsgi:application --timeout 120` (matches the `Procfile`).
4. Verify a sending domain in Resend and point `DEFAULT_FROM_EMAIL` at it.
5. In [cron-job.org](https://cron-job.org), schedule a daily GET to
   `https://<your-app>.onrender.com/internal/trigger-pipeline/?token=<PIPELINE_TRIGGER_TOKEN>`
   at `18:30 UTC` (12:00 AM IST), with retry-on-failure enabled (Render's free tier sleeps after
   15 minutes idle, so the first hit of the day may need a retry while it cold-starts).

## App structure

- `accounts` — organizations, users, auth, email verification, digest enable/disable
- `taxonomy` — canonical product tags, aliases, user tag selection
- `intel` — vulnerability records, scoring, matching, AI enrichment (global, not tenant-scoped)
- `ingestion` — NVD/KEV/EPSS clients, the daily pipeline, the DB-backed run lock
- `digests` — digest snapshots, email rendering, Resend delivery, retry handling

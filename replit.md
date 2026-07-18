# NAUB Enquiry Chatbot

An AI-powered student enquiry chatbot for **Nigerian Army University Biu (NAUB)**, built with Django and a TF-IDF + Cosine Similarity NLP engine.

## How to run

The app starts automatically via the **Start application** workflow (`bash replit_start.sh`), which:
1. Installs Python dependencies from `requirements.txt`
2. Runs Django migrations (SQLite, no external database needed)
3. Loads the knowledge base from `chatbot/knowledge_base.json`
4. Collects static files
5. Starts Gunicorn on port 5000

## Key URLs

- `/chat/` — main chatbot interface (public, no login required)
- `/dashboard/` — admin dashboard (staff login required)
- `/admin/` — Django admin

## Creating an admin account

Open the Shell tab and run:
```bash
python manage.py createsuperuser
```

## Stack

- **Backend**: Python 3.12 · Django 5 · django-allauth · Gunicorn · WhiteNoise
- **NLP**: scikit-learn (TF-IDF / cosine similarity) · NLTK
- **Database**: SQLite (dev/Replit) — set `DATABASE_URL` secret for PostgreSQL
- **Auth**: Username/email login + Google OAuth (credentials needed — see below)

## Environment variables / secrets

| Secret | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | Insecure placeholder (fine for dev) |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `*` |
| `DATABASE_URL` | PostgreSQL connection string | Not set (uses SQLite) |

## Google Sign-In

To enable Google OAuth, either:
- Set real credentials in `naub_chatbot/settings.py` under `SOCIALACCOUNT_PROVIDERS['google']`, or
- Add a Social Application via `/admin/` → Social Applications

## Project structure

```
naub_chatbot/      Django project settings & root URLs
chatbot/           Core chat app: models, NLP engine, views, knowledge base
accounts/          Auth, Google sign-in, onboarding
dashboard/         Admin dashboard (accuracy stats, unanswered queue, KB manager)
static/css/        NAUB-themed stylesheet
templates/         Base template
```

## Missing packages added to requirements.txt

`PyJWT>=2.8` and `cryptography>=42.0` were missing from the original `requirements.txt` (required by django-allauth's Google provider). Both have been added.

## User preferences

_(None set yet)_

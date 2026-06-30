# NAUB Enquiry Chatbot

An AI-powered student enquiry chatbot for **Nigerian Army University Biu (NAUB)**, built with Django and a TF-IDF + Cosine Similarity matching engine (NLTK + scikit-learn).

## Features

- **Chat UI** themed around NAUB's green/gold branding, with typing indicators, suggested-question chips, and a responsive layout.
- **TF-IDF / Cosine Similarity matching engine** (`chatbot/nlp_engine.py`) implementing the 5-phase pipeline described in Chapter 3 of the project report: pre-processing → vectorization → similarity matching → response retrieval → logging.
- **Gibberish detection** that runs before any database write — nonsense input (e.g. "asdkjf laksjdf") gets a polite "please rephrase" reply and is never stored.
- **New Chat** clears the visible conversation but every question is still permanently recorded in `ConversationLog` for analytics.
- **Admin Dashboard** (`/dashboard/`, staff-only):
  - Overview with accuracy %, average match confidence, 7-day answered/unanswered trend chart, and top-matched intents.
  - **Unanswered Questions** queue — admins type an answer once, and it's automatically added to the knowledge base so the bot answers it correctly for everyone going forward.
  - **Knowledge Base** manager — enable/disable intents.
  - **Conversation Logs** — full searchable history of every question asked.
- **Google Sign-In** via django-allauth, plus guest access (no login required to chat).
- **Starter knowledge base** (`chatbot/knowledge_base.json`) covering NAUB admissions, fees, hostels, faculties, programmes, academic calendar, contacts, etc. — intended as a starting point to be refined with official NAUB data later.

## Tech Stack

Python · Django · scikit-learn (TF-IDF, Cosine Similarity) · NLTK · SQLite (dev) / PostgreSQL (production) · django-allauth · Vanilla JS/CSS frontend.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py load_kb          # loads chatbot/knowledge_base.json into the DB
python manage.py createsuperuser  # for /dashboard/ and /admin/ access

python manage.py runserver
```

Visit `http://127.0.0.1:8000/chat/` for the chatbot, and `http://127.0.0.1:8000/dashboard/` (staff login required) for the admin dashboard.

### Google Sign-In

Set real credentials in `naub_chatbot/settings.py` under `SOCIALACCOUNT_PROVIDERS['google']`, or configure a Social Application via `/admin/`.

## Updating the Knowledge Base

Edit `chatbot/knowledge_base.json` and re-run:

```bash
python manage.py load_kb
```

Or use the **Unanswered Questions** panel in the dashboard to add answers directly through the UI — no JSON editing required.

## Project Structure

```
naub_chatbot/      - Django project settings & root URLs
chatbot/           - Core chat app: models, NLP engine, views, knowledge base
accounts/          - Auth, Google sign-in, onboarding
dashboard/         - Admin dashboard app
static/css/        - NAUB-themed stylesheet
templates/          - Base template
```

#!/usr/bin/env bash
# Replit startup script -- runs every time you hit "Run".
# Not used by Render or local development.
set -e

pip install -r requirements.txt --quiet

python manage.py migrate --noinput
python manage.py load_kb
python manage.py collectstatic --noinput

# Auto-create superuser from env vars if they are set and no superuser exists yet
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput 2>/dev/null || true
fi

# Replit's free tier has a persistent filesystem while the Repl is active,
# so SQLite (the default when no DATABASE_URL is set) works fine here.
# If you later add an external Postgres (e.g. Neon/Supabase) and set
# DATABASE_URL as a Replit Secret, it will be picked up automatically.

gunicorn naub_chatbot.wsgi:application --bind 0.0.0.0:5000

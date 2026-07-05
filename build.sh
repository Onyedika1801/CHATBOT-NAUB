#!/usr/bin/env bash
# Render.com build script -- runs automatically on every deploy.
# Not used by Replit or local development.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py load_kb

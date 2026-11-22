#!/usr/bin/env bash
# Render build step
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
# Demo accounts and products (safe to run repeatedly). Remove this line to start empty.
python manage.py seed_demo

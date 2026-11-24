#!/usr/bin/env bash
# Build/release steps for production (used by render.yaml; works on any host).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py ensure_admin

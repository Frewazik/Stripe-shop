#!/usr/bin/env sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# На Free-тарифе Render нет shell/one-off jobs, поэтому суперюзер и демо-данные
# создаются здесь
python manage.py createsuperuser --noinput || true
python manage.py seed_demo || true

# Render/облако задают порт через $PORT; локально/в compose по умолчанию 8000.
exec gunicorn core.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 3

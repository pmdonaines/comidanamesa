#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
python << END
import sys
import time
import psycopg

max_tries = 30
tries = 0

while tries < max_tries:
    try:
        conn = psycopg.connect("${DATABASE_URL}")
        conn.close()
        print("PostgreSQL is ready!")
        sys.exit(0)
    except Exception as e:
        tries += 1
        print(f"PostgreSQL is unavailable - sleeping (attempt {tries}/{max_tries})")
        time.sleep(1)

print("Could not connect to PostgreSQL")
sys.exit(1)
END

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Creating default superuser..."
python << END
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comidanamesa.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin')
    print('Superuser "admin" created successfully!')
else:
    print('Superuser "admin" already exists.')
END

echo "Populating criteria..."
uv run python manage.py popular_criterios --noinput 2>/dev/null || echo "Criteria already populated"

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec "$@"

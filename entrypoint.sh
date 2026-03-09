#!/bin/bash
set -e

echo "=== VoiceHR Startup ==="

# ---- Wait for PostgreSQL to be ready ----
echo "Waiting for PostgreSQL..."
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

while ! python -c "import socket,sys; s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(2); rc=s.connect_ex(('${DB_HOST}', int('${DB_PORT}'))); s.close(); sys.exit(0 if rc==0 else 1)"; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready!"

# ---- Run Migrations ----
echo "Running migrations..."
python manage.py migrate --noinput

# ---- Seed Data (safe - uses get_or_create) ----
echo "Seeding sample data..."
python manage.py seed_data

# ---- Collect Static Files ----
echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

# ---- Start Server ----
echo ""
echo "============================================"
echo "  VoiceHR is running at http://localhost:8000"
echo "============================================"
echo ""
python manage.py runserver 0.0.0.0:8000

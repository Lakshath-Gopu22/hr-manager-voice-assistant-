#!/bin/bash
set -e

echo "=== VoiceHR Startup ==="

# ---- Wait for PostgreSQL to be ready ----
echo "Waiting for PostgreSQL..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('db', 5432))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
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

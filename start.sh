#!/bin/bash
set -e

echo "=== ShiftManager startup ==="

# Debug: show if DATABASE_URL is set (mask password)
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL is not set, using default (localhost)"
else
    echo "DATABASE_URL is set ($(echo $DATABASE_URL | sed 's|://[^@]*@|://***@|'))"
fi

# Wait for database to be reachable
echo "Waiting for database..."
for i in $(seq 1 30); do
    if python -c "
import asyncio, sys
from app.core.config import settings
async def check():
    try:
        import asyncpg
        url = settings.ASYNC_DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://', 1)
        conn = await asyncio.wait_for(asyncpg.connect(url), timeout=3)
        await conn.close()
        return True
    except Exception:
        return False
sys.exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    echo "  attempt $i/30 - database not ready, retrying in 2s..."
    sleep 2
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Running seed data..."
python -m app.utils.seed

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

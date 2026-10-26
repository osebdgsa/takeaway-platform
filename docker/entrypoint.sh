#!/bin/sh
# Wait for PostgreSQL, apply migrations, then hand over to the CMD.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Waiting for database..."
  python - <<'PY'
import sys
import time

from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
for attempt in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is reachable.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"  attempt {attempt}/30 failed: {exc}")
        time.sleep(2)
print("Database did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

  echo "Applying migrations..."
  alembic upgrade head
fi

exec "$@"

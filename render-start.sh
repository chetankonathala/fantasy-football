#!/bin/bash
set -e

echo "==> Running Alembic migrations..."
uv run alembic upgrade head

echo "==> Seeding dynasty values if table is empty..."
uv run python - <<'EOF'
import os, sys
sys.path.insert(0, ".")
from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import DynastyValue
db = get_session_factory()()
count = db.query(DynastyValue).count()
db.close()
if count == 0:
    print("Dynasty table empty — running initial seed...")
    from scripts.refresh_dynasty import refresh_dynasty
    n = refresh_dynasty()
    print(f"Seeded {n} dynasty entries.")
else:
    print(f"Dynasty table has {count} rows — skipping seed.")
EOF

echo "==> Starting uvicorn..."
exec uv run uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

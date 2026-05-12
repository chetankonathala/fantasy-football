#!/bin/bash
set -e

echo "==> Running Alembic migrations..."
uv run alembic upgrade head

echo "==> Seeding dynasty + offseason tables if empty..."
uv run python - <<'EOF'
import sys
sys.path.insert(0, ".")
from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import DynastyValue, RookiePick, OffseasonMove

db = get_session_factory()()
dynasty_count = db.query(DynastyValue).count()
rookie_count = db.query(RookiePick).count()
move_count = db.query(OffseasonMove).count()
db.close()

if dynasty_count == 0:
    print("Dynasty table empty — seeding...")
    from scripts.refresh_dynasty import refresh_dynasty
    print(f"  Seeded {refresh_dynasty()} dynasty entries.")
else:
    print(f"Dynasty table has {dynasty_count} rows.")

if rookie_count == 0:
    print("Rookie table empty — seeding...")
    try:
        from scripts.refresh_rookies import refresh_rookies
        print(f"  Seeded {refresh_rookies()} rookies.")
        from scripts.refresh_nfl_draft import refresh_nfl_draft
        result = refresh_nfl_draft()
        print(f"  Backfilled draft slots: {result}")
    except Exception as e:
        print(f"  Rookie seed failed (non-fatal): {e}")
else:
    print(f"Rookie table has {rookie_count} rows.")

if move_count == 0:
    print("Offseason moves table empty — seeding...")
    try:
        from scripts.refresh_offseason_moves import refresh_offseason_moves
        print(f"  Seeded {refresh_offseason_moves()} moves.")
    except Exception as e:
        print(f"  Moves seed failed (non-fatal): {e}")
else:
    print(f"Offseason moves table has {move_count} rows.")
EOF

echo "==> Starting uvicorn..."
exec uv run uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

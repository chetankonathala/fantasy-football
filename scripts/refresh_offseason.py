#!/usr/bin/env python3
"""Offseason data refresh — runs weekly via Render cron every Monday 9am ET.

Refreshes: rookies, offseason moves, NFL draft slots, depth charts,
strength of schedule, dynasty projections.

On failure: logs error per module, continues to next, exits non-zero
so Render marks the cron run as failed and alerts.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

STEPS = [
    ("refresh_rookies",             "refresh_rookies"),
    ("refresh_offseason_moves",     "refresh_offseason_moves"),
    ("refresh_nfl_draft",           "refresh_nfl_draft"),
    ("refresh_depth_charts",        "refresh_depth_charts"),
    ("refresh_sos",                 "refresh_sos"),
    ("refresh_dynasty_projections", "refresh_projections"),
]

errors = []
for module_name, fn_name in STEPS:
    try:
        log.info(f"Starting {module_name}...")
        mod = __import__(f"scripts.{module_name}", fromlist=[fn_name])
        result = getattr(mod, fn_name)()
        log.info(f"  {module_name} done: {result}")
    except Exception as exc:
        log.error(f"  {module_name} FAILED: {exc}", exc_info=True)
        errors.append(module_name)

if errors:
    log.error(f"Offseason refresh completed with errors in: {', '.join(errors)}")
    sys.exit(1)

log.info("Offseason refresh complete — all steps succeeded.")

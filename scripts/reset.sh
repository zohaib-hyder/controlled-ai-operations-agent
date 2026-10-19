#!/bin/sh
# Never delete the shared Compose volume. Only the marked dedicated demo DB is reset.
set -eu
if [ "${1:-}" != "--confirm-synthetic-reset" ]; then
  echo "WARNING: deletes the marked local northstar_demo database contents."
  echo "Set DATABASE_URL explicitly; then: sh scripts/reset.sh --confirm-synthetic-reset"
  exit 1
fi
exec backend/.venv/bin/python scripts/demo_database.py --confirm-synthetic-reset

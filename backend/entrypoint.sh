#!/usr/bin/env bash
set -euo pipefail

ROLE="${APP_ROLE:-api}"

if [ "$ROLE" = "api" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head

  if [ -n "${BOOTSTRAP_ADMIN_MAX_ID:-}" ] && [ -n "${BOOTSTRAP_ADMIN_FULL_NAME:-}" ]; then
    echo "[entrypoint] ensuring bootstrap platform administrator"
    python -m app.cli.platform_admin \
      --max-user-id "$BOOTSTRAP_ADMIN_MAX_ID" \
      --full-name "$BOOTSTRAP_ADMIN_FULL_NAME"
  fi

  if [ "${DEMO_SEED:-false}" = "true" ]; then
    echo "[entrypoint] loading demo data"
    python -m app.cli.demo_seed
  fi
fi

exec "$@"

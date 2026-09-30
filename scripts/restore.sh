
set -euo pipefail

DB_FILE="${1:?usage: $0 <db.sql.gz> [uploads.tar.gz]}"
UPLOADS_FILE="${2:-}"
COMPOSE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DC="docker compose -f $COMPOSE"

echo "→ restoring DB from $DB_FILE"
gunzip -c "$DB_FILE" | $DC exec -T db sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if [ -n "$UPLOADS_FILE" ]; then
  echo "→ restoring uploads from $UPLOADS_FILE"
  docker run --rm \
    -v "$(docker volume ls -q | grep -E 'uploads-data$' | head -1):/data" \
    -v "$(dirname "$(realpath "$UPLOADS_FILE")")":/backup:ro \
    alpine:3 \
    sh -c "cd /data && tar xzf /backup/$(basename "$UPLOADS_FILE")"
fi

echo "done. Verify with: $DC exec backend python -c 'from app.db.session import SessionLocal; print(SessionLocal().execute(__import__(\"sqlalchemy\").text(\"select count(*) from users\")).scalar())'"

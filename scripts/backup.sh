
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
COMPOSE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DC="docker compose -f $COMPOSE"
STAMP="$(date -u +%Y-%m-%d-%H%M)"

mkdir -p "$BACKUP_DIR"

# 1) Дамп БД через exec в контейнер db. -Fc — собственный формат для pg_restore.
DB_FILE="$BACKUP_DIR/db-$STAMP.sql.gz"
echo "→ db dump → $DB_FILE"
$DC exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' | gzip > "$DB_FILE"

# 2) Uploads (отдельный named volume). Через временный контейнер, чтобы не зависеть
#    от состояния backend.
UPLOADS_FILE="$BACKUP_DIR/uploads-$STAMP.tar.gz"
echo "→ uploads tar → $UPLOADS_FILE"
docker run --rm \
  -v "$(docker volume ls -q | grep -E 'uploads-data$' | head -1):/data:ro" \
  -v "$BACKUP_DIR":/backup \
  alpine:3 \
  sh -c "cd /data && tar czf /backup/$(basename "$UPLOADS_FILE") ."

# 3) (Опционально) S3
if [ -n "${AWS_S3_BUCKET:-}" ]; then
  echo "→ uploading to s3://$AWS_S3_BUCKET/mfc-max/"
  aws s3 cp "$DB_FILE" "s3://$AWS_S3_BUCKET/mfc-max/"
  aws s3 cp "$UPLOADS_FILE" "s3://$AWS_S3_BUCKET/mfc-max/"
fi

# 4) Очистка локально — оставляем последние 30 файлов каждого типа.
echo "→ cleanup (keep last 30)"
ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm --
ls -1t "$BACKUP_DIR"/uploads-*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm --

echo "done."

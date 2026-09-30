# Development workflow

## Dev stack

The live local stack uses `docker-compose.dev.yml` — not the root `docker-compose.yml`, which is closer to a deploy shape. Backend source is bind-mounted into its container, so most backend edits apply on container restart without a rebuild. `frontend-admin` and `frontend-miniapp` ship as static builds behind nginx, so their edits need an image rebuild to show up in the running stack.

```bash
make dev-up                                    # build + start the full dev stack
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f backend
```

Ports: backend `8000`, admin `5173`, mini-app `5174`, bot webhook gateway `8080`, Postgres `5432`, Redis `6379`.

`frontend-miniapp` bakes `VITE_API_URL` (from `.env`'s `PUBLIC_API_URL`) into its static build at image-build time — it does **not** use the `vite dev` proxy in this compose setup, since it's served pre-built by nginx. If `.env` points `PUBLIC_API_URL` at a remote host (this can happen deliberately, e.g. to test the mini-app against a shared staging backend), the mini-app in this local stack will talk to that remote backend, not `localhost:8000`, and any backend endpoint you're actively developing locally won't be reachable from it (CORS-blocked, and the code isn't deployed there anyway). To browser-test the mini-app against your local backend, temporarily set `PUBLIC_API_URL=http://localhost:8000`, rebuild `frontend-miniapp`, test, then restore the original value and rebuild again.

## Backend

```bash
docker compose -f docker-compose.dev.yml exec backend pytest -q [path]
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
docker compose -f docker-compose.dev.yml exec backend alembic downgrade -1   # verify a new migration reverses cleanly, then upgrade again
```

`uvicorn` runs without `--reload` in this compose file. After a backend code change you want live in the running stack:

```bash
docker compose -f docker-compose.dev.yml restart backend
```

## Frontend (admin / mini-app)

```bash
cd frontend-admin && npx tsc --noEmit && npm run build   # matches the real `npm run build` gate; `npm run lint` is currently broken (eslint isn't a declared devDependency)
```

To see frontend changes in the running dev stack, rebuild the image — bind-mounting doesn't apply to it:

```bash
docker compose -f docker-compose.dev.yml up -d --build frontend-admin
```

## Known gotcha: 502 after restarting `backend`

`frontend-admin`'s nginx resolves the `backend` upstream once, at its own startup, and does not re-resolve it afterwards (`proxy_pass http://backend:8000/...` with a static hostname). If `backend` is restarted (or recreated) *after* `frontend-admin` was last started, requests proxied through `frontend-admin` → `/api/*` can start returning `502 Bad Gateway` with **nothing in the backend logs** — the request never reaches it.

Symptom to recognize: `curl localhost:8000/api/...` works directly, but `curl localhost:5173/api/...` 502s.

Fix: restart `frontend-admin` too, so its nginx re-resolves `backend`'s current address.

```bash
docker compose -f docker-compose.dev.yml restart frontend-admin
```

A durable fix (not yet applied, touches the nginx config used by both dev and prod images — confirm before changing) is to make `frontend-admin/nginx.conf` re-resolve dynamically instead of caching forever, e.g. `resolver 127.0.0.11 valid=10s;` (Docker's embedded DNS) plus a variable-based `proxy_pass`.

## Minting an authenticated admin session for scripted/browser QA

There is no dev login bypass; the only real login path validates MAX `initData`. To drive the admin panel with a script or headless browser without that, mint a real refresh session directly using the app's own use case, from inside the `backend` container (importing `app.main` first registers the full SQLAlchemy mapper graph, which a standalone script otherwise lacks):

```python
import app.main
from app.db.session import SessionLocal
from app.core.config import settings
from app.modules.admin_sessions.application.services import StartAdminSession
from app.modules.admin_sessions.infrastructure.repositories import HmacRefreshTokenCodec, SqlAlchemyAdminSessionRepository

db = SessionLocal()
issued = StartAdminSession(
    SqlAlchemyAdminSessionRepository(db),
    HmacRefreshTokenCodec(),
    refresh_days=settings.ADMIN_REFRESH_EXPIRES_DAYS,
    absolute_days=settings.ADMIN_SESSION_ABSOLUTE_DAYS,
).execute(<admin_id>, user_agent="qa-script", ip="127.0.0.1")
db.commit()
print(issued.raw_token)
```

Then, before navigating the browser to `http://localhost:5173`, set two cookies (same-origin, domain `localhost` — the admin API is deliberately same-origin, see `frontend-admin/src/api/config.ts`):

- `platform_admin_refresh` = the printed raw token; `httpOnly`; `path=/api/auth`
- `platform_admin_csrf` = any non-empty string; **not** httpOnly; `path=/` — this is a pure double-submit check (the backend only compares the cookie against the `X-CSRF-Token` header the frontend echoes back from it), not tied to a server-stored value

The SPA's `restoreSession()` on mount calls `POST /api/auth/admin/refresh` using those cookies and populates a real logged-in session — no code changes or bypasses needed.

No `chromium-cli` or Playwright is preinstalled in this environment; `npm install playwright && npx playwright install chromium` in a scratch directory works (don't add it to `frontend-admin/package.json` as a side effect of QA).

**Clean up test artifacts afterwards**: rows in `admin_refresh_sessions` tagged with your `user_agent`, any bot instances you created (`bot_instances` / `bot_runtimes` tables), and their entries in `/app/secrets/bots.env` inside the `backend` container. Leave `audit_log` rows alone — it's an audit trail, not scratch data.

"""Re-provisions every bot's `runtime_token_hash` after Task 053 changed how
`hash_runtime_token()` signs it (raw HMAC over JWT_SECRET -> a purpose-derived subkey, see
`app.core.security.HmacPurpose`). Every `BotRuntimeRecord` whose hash was written before that
change now fails `authorize_bot_runtime()` for every backend call the bot process makes
(settings reads, consent status/accept/revoke, message ingress, campaign-link tracking) with
401 `invalid_bot_runtime_token` -- and since `bot/app/backend.py` catches those failures and
falls back to safe defaults instead of surfacing them, the bot silently shows a hardcoded
fallback start message, an incorrect consent gate, etc. instead of erroring loudly.

There is no way to detect "was this hash signed under the old scheme" from the hash alone
(that's the point of a hash) -- this rotates *every* row with a non-null `runtime_token_hash`
unconditionally. Rotating one that's already on the new scheme is harmless: a bot only ever
authenticates with the runtime token this same command hands back or writes to the managed
store, so nothing was relying on the old plaintext still working.

Two different remediation paths depending on `credential_source` (see runtime_router.py):

- "managed": re-provisioning writes the new token straight into the managed env file
  (`BOT_MANAGED_ENV_FILE`) that `bot/app/supervisor.py` already re-reads every poll cycle
  (`BOT_SUPERVISOR_INTERVAL_SECONDS`, default 10s) -- no manual step, the supervisor respawns
  that bot's process with the new token on its own within one poll interval.
- "environment" (or unset): the token only ever lived in this command's one-time output and
  whatever env var the bot container reads it from -- there's nothing else to write it to, so
  this prints the new plaintext token and the exact env var name, and the operator has to set it
  on that bot's process and restart it. Until that happens this bot is *worse off than before
  running this command*: its old (mismatched) hash is gone, so it's now guaranteed to fail
  auth rather than only failing on the code paths this bug already broke -- run this only when
  ready to immediately apply the printed token.

Usage (inside the backend container):
    python -m app.cli.reprovision_bot_runtime_tokens              # rotate every affected bot
    python -m app.cli.reprovision_bot_runtime_tokens --bot-id 7   # just one bot
    python -m app.cli.reprovision_bot_runtime_tokens --dry-run    # list affected bots, change nothing
"""

from __future__ import annotations

import argparse
import secrets

from sqlalchemy import select

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata; AuditLog's
# admin_id FK and several models' string-referenced relationships only resolve once the whole
# mapper registry is populated, not just the modules this script otherwise imports directly.
from ..core.config import settings
from ..db.session import SessionLocal
from ..modules.audit.infrastructure.models import AuditLog
from ..modules.bot_instances.application.runtime_credentials import (
    ManagedBotTokenMissing,
    ProvisionManagedCredential,
    ProvisionManagedCredentialCommand,
)
from ..modules.bot_instances.domain.runtime_credentials import runtime_token_env_key
from ..modules.bot_instances.infrastructure.env_file_credentials import (
    EnvFileRuntimeCredentialStore,
)
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord, BotRuntimeRecord
from ..services.bot_runtime_auth import hash_runtime_token


def _affected(db, bot_id: int | None) -> list[BotRuntimeRecord]:
    stmt = select(BotRuntimeRecord).where(BotRuntimeRecord.runtime_token_hash.is_not(None))
    if bot_id is not None:
        stmt = stmt.where(BotRuntimeRecord.bot_instance_id == bot_id)
    return list(db.execute(stmt).scalars())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--bot-id", type=int, default=None, help="Only rotate this bot instance")
    parser.add_argument(
        "--dry-run", action="store_true", help="List affected bots without changing anything"
    )
    args = parser.parse_args()

    store = EnvFileRuntimeCredentialStore(settings.BOT_MANAGED_ENV_FILE)

    with SessionLocal() as db:
        runtimes = _affected(db, args.bot_id)
        if not runtimes:
            print("No bot has a runtime_token_hash set -- nothing to rotate.")
            return

        # `_slug_suffix()` (domain/runtime_credentials.py) collapses any run of non-alphanumerics
        # to `_`, so e.g. slugs "foo-bar" and "foo_bar" derive the *same* managed-store key --
        # two real bots found sharing one this way while testing this script (ids 14 and 15,
        # "vysshee_obrazovanie_rut" / "vysshee-obrazovanie-rut"). Rotating both of a colliding
        # pair in one run silently corrupts whichever gets written first with the other's token
        # -- a pre-existing bug in the credential-key derivation, not something this script can
        # fix, so it refuses to touch either side of a collision rather than pick a winner.
        managed_bots = {
            runtime.bot_instance_id: db.get(BotInstanceRecord, runtime.bot_instance_id)
            for runtime in runtimes
            if runtime.credential_source == "managed"
        }
        by_env_key: dict[str, list[str]] = {}
        for bot_id, bot in managed_bots.items():
            if bot is None:
                continue
            key = runtime_token_env_key(bot.slug)
            by_env_key.setdefault(key, []).append(f"#{bot_id} ({bot.slug})")
        colliding_bot_ids: set[int] = set()
        for key, labels in by_env_key.items():
            if len(labels) > 1:
                print(f"COLLISION on managed-store key {key}: {', '.join(labels)} -- skipping all of them")
                colliding_bot_ids.update(
                    bot_id for bot_id, bot in managed_bots.items()
                    if bot is not None and f"#{bot_id} ({bot.slug})" in labels
                )

        for runtime in runtimes:
            if runtime.bot_instance_id in colliding_bot_ids:
                continue
            bot = db.get(BotInstanceRecord, runtime.bot_instance_id)
            label = f"bot #{runtime.bot_instance_id} ({bot.slug if bot else 'unknown slug'})"

            if args.dry_run:
                print(f"{label}: would rotate ({runtime.credential_source or 'environment'})")
                continue

            if runtime.credential_source == "managed":
                if bot is None:
                    print(f"{label}: SKIPPED -- bot instance row is gone")
                    continue
                try:
                    provisioned = ProvisionManagedCredential(store).execute(
                        ProvisionManagedCredentialCommand(
                            bot_slug=bot.slug, bot_token=None, mode=runtime.mode
                        )
                    )
                except ManagedBotTokenMissing:
                    print(
                        f"{label}: SKIPPED -- managed store has no MAX bot token saved for it "
                        "(re-save its credential in the admin panel instead)"
                    )
                    continue
                runtime.runtime_token_hash = hash_runtime_token(provisioned.runtime_token)
                runtime.last_seen_at = None
                runtime.last_error_code = None
                db.add(
                    AuditLog(
                        admin_id=None,
                        bot_instance_id=runtime.bot_instance_id,
                        method="CLI",
                        path="bot-instances:reprovision-runtime-token",
                        status_code=200,
                        meta={"action": "runtime_token_reprovisioned", "credential_source": "managed"},
                    )
                )
                # Committed per-bot, right after the store write above, not batched at the end:
                # `store.set_many()` already landed on disk and can't be rolled back with the DB
                # transaction, so if this commit fails, the store's new token and the DB's old
                # hash would otherwise go out of sync for every bot in the batch, not just this
                # one -- see this module's docstring on why a stale hash is worse than none.
                db.commit()
                print(f"{label}: rotated (managed) -- supervisor will pick it up within one poll interval")
            else:
                token = secrets.token_urlsafe(32)
                runtime.runtime_token_hash = hash_runtime_token(token)
                runtime.last_seen_at = None
                runtime.last_error_code = None
                db.add(
                    AuditLog(
                        admin_id=None,
                        bot_instance_id=runtime.bot_instance_id,
                        method="CLI",
                        path="bot-instances:reprovision-runtime-token",
                        status_code=200,
                        meta={"action": "runtime_token_reprovisioned", "credential_source": "environment"},
                    )
                )
                db.commit()
                env_key = runtime_token_env_key(bot.slug) if bot else "BOT_RUNTIME_TOKEN"
                print(
                    f"{label}: rotated (environment) -- set {env_key}={token} on that bot's "
                    "process and restart it NOW; it cannot authenticate until you do"
                )


if __name__ == "__main__":
    main()

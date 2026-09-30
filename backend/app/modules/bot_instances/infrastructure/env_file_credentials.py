from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path


class EnvFileRuntimeCredentialStore:
    """Atomic, locked storage for secrets shared with the bot supervisor."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def contains(self, key: str) -> bool:
        return bool(self._read().get(key))

    def get(self, key: str) -> str | None:
        return self._read().get(key) or None

    def set_many(self, values: dict[str, str]) -> None:
        if not values:
            return
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = self._path.with_suffix(f"{self._path.suffix}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            current = self._read()
            current.update(values)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
                    for key in sorted(current):
                        temporary.write(f"{key}={json.dumps(current[key], ensure_ascii=False)}\n")
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.chmod(temporary_name, 0o600)
                os.replace(temporary_name, self._path)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

    def delete_many(self, keys: list[str]) -> None:
        """Best-effort compensation for a provisioning step that failed after the credential
        was already written (see `ProvisionBotInstance`) — not a hard guarantee, since a crash
        between `set_many` and this call still leaves an orphaned entry, but it closes the
        common failure path where a later in-process step raises."""
        if not keys:
            return
        if not self._path.exists():
            return
        lock_path = self._path.with_suffix(f"{self._path.suffix}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            current = self._read()
            if not any(key in current for key in keys):
                return
            for key in keys:
                current.pop(key, None)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
                    for key in sorted(current):
                        temporary.write(f"{key}={json.dumps(current[key], ensure_ascii=False)}\n")
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.chmod(temporary_name, 0o600)
                os.replace(temporary_name, self._path)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        result: dict[str, str] = {}
        for raw_line in self._path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw_value = line.split("=", 1)
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                value = raw_value
            if key and isinstance(value, str):
                result[key] = value
        return result

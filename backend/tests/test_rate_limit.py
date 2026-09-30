from collections import defaultdict

import pytest
from starlette.requests import Request

from app.core.errors import ApiError
from app.core.security import create_access_token
from app.services import rate_limit as rate_limit_module


class RedisCounter:
    def __init__(self) -> None:
        self.values: dict[str, int] = defaultdict(int)
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] += 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)


def _request(bot_slug: str, token: str | None = None) -> Request:
    headers = [(b"x-bot-slug", bot_slug.encode())]
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request({"type": "http", "headers": headers})


def test_session_limit_is_isolated_by_bot_slug(monkeypatch) -> None:
    redis = RedisCounter()
    monkeypatch.setattr(rate_limit_module, "redis_client", redis)
    dependency = rate_limit_module.rate_limit("message", limit=1, window_seconds=60)
    token = create_access_token({"sub": "u:7", "role": "student"})

    dependency(_request("bot-a", token))
    dependency(_request("bot-b", token))

    assert len(redis.values) == 2
    assert all(value == 1 for value in redis.values.values())
    assert any(":bot-a:session:" in key for key in redis.values)
    assert any(":bot-b:session:" in key for key in redis.values)


def test_limit_rejects_limit_plus_one(monkeypatch) -> None:
    redis = RedisCounter()
    monkeypatch.setattr(rate_limit_module, "redis_client", redis)
    dependency = rate_limit_module.rate_limit("staff", limit=2, window_seconds=45)
    request = _request("default", create_access_token({"sub": "a:3", "role": "admin"}))

    dependency(request)
    dependency(request)
    with pytest.raises(ApiError) as error:
        dependency(request)

    assert error.value.status_code == 429
    assert error.value.detail["retry_after"] == 45


def test_max_user_limit_uses_opaque_identity_and_tenant(monkeypatch) -> None:
    redis = RedisCounter()
    monkeypatch.setattr(rate_limit_module, "redis_client", redis)
    identity = rate_limit_module.max_user_rate_identity("max", "123456789")

    rate_limit_module.enforce_rate_limit(
        "ingress", limit=2, window_seconds=30, tenant="hr", identity=identity
    )

    key = next(iter(redis.values))
    assert ":hr:max-user:" in key
    assert "123456789" not in key


def test_request_without_session_uses_anonymous_bucket(monkeypatch) -> None:
    redis = RedisCounter()
    monkeypatch.setattr(rate_limit_module, "redis_client", redis)
    dependency = rate_limit_module.rate_limit("anonymous", limit=1, window_seconds=30)

    dependency(_request("default"))

    assert redis.values["rl:anonymous:default:anonymous"] == 1

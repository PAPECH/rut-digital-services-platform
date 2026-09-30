import json
from types import SimpleNamespace

from app.services import push


class RedisRecorder:
    def __init__(self) -> None:
        self.calls = []

    def rpush(self, key, value) -> None:
        self.calls.append((key, json.loads(value)))


def test_push_queue_is_routed_by_bot_slug(monkeypatch) -> None:
    recorder = RedisRecorder()
    monkeypatch.setattr(push, "redis_client", recorder)
    user = SimpleNamespace(
        id=7,
        user_id="external-7",
        system=SimpleNamespace(value="max"),
        language_code="ru",
    )
    item = push._redis_item(
        user=user,
        bot_slug="personnel",
        kind="admission_rating_changed",
        payload={"installation_id": 11},
    )

    push._push_to_redis(item)

    assert recorder.calls[0][0] == "max:personnel:push:queue"
    assert recorder.calls[0][1]["bot_slug"] == "personnel"
    assert recorder.calls[0][1]["payload"] == {"installation_id": 11}

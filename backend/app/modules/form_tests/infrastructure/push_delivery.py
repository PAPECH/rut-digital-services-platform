from __future__ import annotations

from sqlalchemy.orm import Session

from ....services.push import enqueue_push
from ..domain.message_split import split_message

# `maxapi.methods.send_message.SendMessage.__init__` raises `ValueError` for
# `len(text) >= 4000` -- one below the documented "до 4000 символов" server-side limit, kept
# here rather than 4000 exactly so this stays correct even if the library's own bound changes
# by a hair.
MAX_MESSAGE_LENGTH = 3999


class PushResultDeliveryGateway:
    """Delivers a completed attempt's result as one or more MAX chat messages through the
    platform's existing transactional push mechanism -- no new delivery infrastructure (Task
    068's Non-goals: no e-mail sending). A `test_result` row's payload always carries a single
    chunk already under MAX's message-length limit; `bot/app/push.py::_format_message` returns
    it verbatim."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def deliver_result(self, *, bot_instance_id: int, user_id: int, text: str) -> None:
        for chunk in split_message(text, MAX_MESSAGE_LENGTH):
            enqueue_push(
                self._session,
                bot_instance_id=bot_instance_id,
                user_id=user_id,
                kind="test_result",
                payload={"text": chunk},
            )

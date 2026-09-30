from __future__ import annotations

import secrets

from ....core.security import HmacPurpose, hmac_sign


class HmacInviteTokenCodec:
    def generate(self) -> str:
        return secrets.token_urlsafe(32)

    def digest(self, raw_token: str) -> str:
        return hmac_sign(HmacPurpose.ADMIN_INVITE_TOKEN, raw_token)

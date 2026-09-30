from __future__ import annotations

import re

INVITE_START_PARAM_PREFIX = "inv_"

_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{16,200}")


def invite_start_param(raw_token: str) -> str:
    return f"{INVITE_START_PARAM_PREFIX}{raw_token}"


def parse_invite_token(start_param: str | None) -> str | None:
    if not start_param or not start_param.startswith(INVITE_START_PARAM_PREFIX):
        return None
    token = start_param[len(INVITE_START_PARAM_PREFIX) :]
    return token if _TOKEN_RE.fullmatch(token) else None

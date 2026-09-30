"""core/security.py's per-purpose HKDF subkeys (Task 053 audit finding #4) — replaces the old
single shared-JWT_SECRET HMAC primitive used for signed file URLs, content preview tokens,
bot-runtime-token hashing, rate-limit identity hashing, and admin refresh-token digests.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.security import HmacPurpose, _subkey, hmac_sign, hmac_verify


def test_subkeys_differ_across_purposes() -> None:
    keys = {purpose: _subkey(purpose) for purpose in HmacPurpose}
    assert len(set(keys.values())) == len(keys), "every purpose must derive a distinct subkey"


def test_subkeys_differ_from_the_raw_secret() -> None:
    raw = settings.JWT_SECRET.encode("utf-8")
    for purpose in HmacPurpose:
        assert _subkey(purpose) != raw


def test_sign_and_verify_round_trip_for_the_same_purpose() -> None:
    sig = hmac_sign(HmacPurpose.FILE_URL, "42.9999999999")
    assert hmac_verify(HmacPurpose.FILE_URL, "42.9999999999", sig)


def test_a_signature_from_one_purpose_does_not_verify_under_another() -> None:
    # The whole point of per-purpose subkeys: a signature minted for one artifact type must
    # not be replayable as if it were a different artifact type, even for the same message.
    message = "42.9999999999"
    sig = hmac_sign(HmacPurpose.FILE_URL, message)
    assert not hmac_verify(HmacPurpose.CONTENT_PREVIEW, message, sig)
    assert not hmac_verify(HmacPurpose.BOT_RUNTIME_TOKEN, message, sig)


def test_subkey_derivation_is_deterministic() -> None:
    assert _subkey(HmacPurpose.FILE_URL) == _subkey(HmacPurpose.FILE_URL)

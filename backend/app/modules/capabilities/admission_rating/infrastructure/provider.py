from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..application.ports import (
    AdmissionRatingSnapshot,
    ProviderPlan,
    ProviderRating,
)
from ..domain.config import AdmissionRatingConfig
from ..domain.identity import normalize_applicant_code
from .parser import LEVEL_IDS, TRAINING_IDS, parse_plans, parse_ratings

_BASE_URL = "https://miit.ru/api-1c/miit/hs/AdmissionPlan"
_MAX_RESPONSE_BYTES = 8_000_000_000
_MAX_PLANS = 2_000
_MAX_RATINGS = 500_000
_RETRY_DELAYS = (0.0, 0.4, 1.2)


class RutAdmissionProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def provider_error_code(error: BaseException) -> str:
    """Return an operator-safe error code from the fixed RUT provider."""

    if isinstance(error, RutAdmissionProviderError):
        return error.code
    if isinstance(error, httpx.TimeoutException):
        return "provider_timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return "provider_http_error"
    if isinstance(error, httpx.HTTPError):
        return "provider_network_unavailable"
    if isinstance(error, (TypeError, ValueError)):
        return "provider_response_invalid"
    return "provider_unavailable"


class RutAdmissionProvider:
    """Fixed-host RUT adapter with bounded responses and retry/backoff."""

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for delay in _RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.get(path, params=params)
                response.raise_for_status()
                if len(response.content) > _MAX_RESPONSE_BYTES:
                    raise RutAdmissionProviderError("provider_response_too_large")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RutAdmissionProviderError("provider_response_invalid")
                return payload
            except (httpx.HTTPError, ValueError, RutAdmissionProviderError) as exc:
                last_error = exc
        if isinstance(last_error, RutAdmissionProviderError):
            raise last_error
        if isinstance(last_error, httpx.TimeoutException):
            raise RutAdmissionProviderError("provider_timeout") from last_error
        if isinstance(last_error, httpx.HTTPStatusError):
            raise RutAdmissionProviderError("provider_http_error") from last_error
        raise RutAdmissionProviderError("provider_network_unavailable") from last_error

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(connect=5, read=30, write=5, pool=5),
            follow_redirects=False,
            verify=True,
            headers={"Accept": "application/json", "User-Agent": "RUT-MAX-Platform/1.0"},
        )

    async def probe(self, config: AdmissionRatingConfig) -> None:
        async with self._client() as client:
            await self._get_json(
                client,
                "/reception-plan",
                {"city": 1, "level": "50", "year": config.admission_year, "training": "20773"},
            )

    async def read_snapshot(self, config: AdmissionRatingConfig) -> AdmissionRatingSnapshot:
        raw_plans = []
        async with self._client() as client:
            for level in LEVEL_IDS:
                for training in TRAINING_IDS:
                    payload = await self._get_json(
                        client,
                        "/reception-plan",
                        {
                            "city": 1,
                            "level": level,
                            "year": config.admission_year,
                            "training": training,
                        },
                    )
                    try:
                        parsed_plans = parse_plans(payload)
                    except (KeyError, TypeError, ValueError) as exc:
                        raise RutAdmissionProviderError("provider_response_invalid") from exc
                    raw_plans.extend(parsed_plans)
                    if len(raw_plans) > _MAX_PLANS:
                        raise RutAdmissionProviderError("provider_plan_limit_exceeded")

            unique_plans = {plan.plan_id: plan for plan in raw_plans}
            ratings: list[ProviderRating] = []
            for plan in unique_plans.values():
                payload = await self._get_json(
                    client,
                    "/rating",
                    {"year": config.admission_year, "id": plan.plan_id},
                )
                try:
                    parsed_ratings = parse_ratings(payload)
                except (KeyError, TypeError, ValueError) as exc:
                    raise RutAdmissionProviderError("provider_response_invalid") from exc
                for item in parsed_ratings:
                    ratings.append(
                        ProviderRating(
                            plan_id=plan.plan_id,
                            applicant_code=normalize_applicant_code(item.applicant_code),
                            points=item.points,
                            preference=item.preference,
                            competition=item.competition,
                            group_name=item.group_name,
                            position=item.position,
                        )
                    )
                if len(ratings) > _MAX_RATINGS:
                    raise RutAdmissionProviderError("provider_rating_limit_exceeded")

        plans = tuple(
            ProviderPlan(
                plan_id=plan.plan_id,
                specialty=plan.specialty,
                qualification=plan.qualification,
                totals=plan.totals,
            )
            for plan in unique_plans.values()
        )
        return AdmissionRatingSnapshot(plans=plans, ratings=tuple(ratings))

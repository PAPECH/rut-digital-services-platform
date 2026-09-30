from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain.schema import validate_test_schema
from .rut_spt_import import load_rut_spt_elements

_SOURCE_PATH = Path(__file__).resolve().parents[4] / "seed" / "form_tests" / "rut_spt_source.md"


def _terms(prefix: str, numbers: list[int]) -> list[dict[str, Any]]:
    return [{"question_key": f"{prefix}_{n:02d}", "weight": 1.0} for n in numbers]


def _scale(key: str, label: str, terms: list[dict[str, Any]], *, constant: float, aggregation: str) -> dict:
    return {"key": key, "label": label, "terms": terms, "constant": constant, "aggregation": aggregation}


def _build_result_scales() -> list[dict[str, Any]]:
    scales: list[dict[str, Any]] = []

    # Beck depression: plain sum, 0-60 range (Приложение 1: "суммирование номера выбранного
    # пункта"; lettered options like 1а/1б share one score, already reflected per-option).
    scales.append(
        _scale(
            "bdi_total",
            "Депрессивная симптоматика",
            _terms("BDI", range(1, 21)),
            constant=0,
            aggregation="sum",
        )
    )

    # Spielberger-Khanin: RUT's supplied option scores already bake in each item's own
    # direction (see infrastructure.rut_spt_import), so every term here is weight=+1 -- the
    # instrument's official Sigma1-Sigma2+35 offset is captured purely as `constant`.
    # State anxiety needs -15 on top of a naive baked-score sum (10 reverse items x a (5-raw)
    # flip contribute +50, not the +35 the official formula wants); trait anxiety's 7 reverse
    # items already land on +35 exactly, so its constant is 0. See
    # `test_form_tests_scoring.py`'s state/trait asymmetry tests for the worked proof.
    scales.append(
        _scale(
            "stai_state",
            "Ситуативная тревожность",
            _terms("STAI_S", range(1, 21)),
            constant=-15,
            aggregation="sum",
        )
    )
    scales.append(
        _scale(
            "stai_trait",
            "Личностная тревожность",
            _terms("STAI_T", range(1, 21)),
            constant=0,
            aggregation="sum",
        )
    )

    # Academic motivation: 7 subscales, each a fixed 4-item sum, per Приложение 1's scheme
    # (confirmed against the source ТЗ in this conversation).
    ams_subscales = {
        "ams_cognitive": ("Познавательная мотивация", [1, 8, 15, 22]),
        "ams_achievement": ("Мотивация достижения", [2, 9, 16, 23]),
        "ams_self_development": ("Мотивация саморазвития", [3, 10, 17, 24]),
        "ams_self_respect": ("Мотивация самоуважения", [4, 11, 18, 25]),
        "ams_introjected": ("Интроецированная мотивация", [5, 12, 19, 26]),
        "ams_external": ("Экстернальная мотивация", [6, 13, 20, 27]),
        "ams_amotivation": ("Амотивация", [7, 14, 21, 28]),
    }
    for key, (label, numbers) in ams_subscales.items():
        scales.append(_scale(key, label, _terms("AMS", numbers), constant=0, aggregation="sum"))

    # Socio-cultural environment: 4 subscales, sum of already-reversed option scores (Приложение
    # 1's "перевод шкальных оценок" table is already applied per-option in the source content).
    scu_subscales = {
        "scu_spatial_semantic": ("Пространственно-семантический компонент", [1, 6, 11, 16, 19, 21, 23]),
        "scu_content_methodical": ("Содержательно-методический компонент", [2, 3, 8, 9, 12, 14, 15, 22]),
        "scu_communication_organizational": ("Коммуникационно-организационный компонент", [4, 5, 7]),
        "scu_personal_involvement": ("Персональная включенность", [10, 13, 17, 18, 20]),
    }
    for key, (label, numbers) in scu_subscales.items():
        scales.append(_scale(key, label, _terms("SCU", numbers), constant=0, aggregation="sum"))

    # BAT burnout: 4 subscale AVERAGES per Приложение 1's explicit "(sum)/n" formulas, plus an
    # overall score that is the grand mean over all 23 raw items directly -- verified against
    # Schaufeli et al.'s own published BAT scoring ("summing the answers on items 1-23 and
    # dividing by 23"), *not* an average of the 4 subscale averages (those are unequal-sized
    # groups -- 8/5/5/5 items -- so the two are not the same number; the source ТЗ's phrasing
    # ("(истощение + ... )/23") reads ambiguously but the verified instrument confirms the
    # grand-mean-over-raw-items reading).
    bat_exhaustion = _scale(
        "bat_exhaustion", "Истощение", _terms("BAT", range(1, 9)), constant=0, aggregation="mean"
    )
    bat_distancing = _scale(
        "bat_distancing",
        "Внутреннее дистанцирование",
        _terms("BAT", range(9, 14)),
        constant=0,
        aggregation="mean",
    )
    bat_cognitive = _scale(
        "bat_cognitive",
        "Когнитивные затруднения",
        _terms("BAT", range(14, 19)),
        constant=0,
        aggregation="mean",
    )
    bat_emotional = _scale(
        "bat_emotional",
        "Эмоциональные затруднения",
        _terms("BAT", range(19, 24)),
        constant=0,
        aggregation="mean",
    )
    bat_overall = _scale(
        "bat_overall",
        "Учебное выгорание (общий балл)",
        _terms("BAT", range(1, 24)),
        constant=0,
        aggregation="mean",
    )
    scales += [bat_exhaustion, bat_distancing, bat_cognitive, bat_emotional, bat_overall]

    # Basic psychological needs: 3 subscales, sum of already-reversed option scores.
    bpns_subscales = {
        "bpns_autonomy": ("Автономия", [1, 5, 8, 11, 13, 17, 20]),
        "bpns_competence": ("Компетентность", [3, 4, 10, 12, 14, 19]),
        "bpns_relatedness": ("Связность", [2, 6, 7, 9, 15, 16, 18, 21]),
    }
    for key, (label, numbers) in bpns_subscales.items():
        scales.append(_scale(key, label, _terms("BPNS", numbers), constant=0, aggregation="sum"))

    # SURPS: 4 subscales, sum of already-reversed option scores -- verified against Woicik,
    # Stewart, Pihl & Conrod (2009): plain "reverse-code then sum", no scale-level constant
    # (unlike Spielberger-Khanin's +35 quirk). Item-direction split matches the publication's
    # own Hopelessness breakdown (6 reverse / 1 direct) exactly.
    surps_subscales = {
        "surps_hopelessness": ("Безнадежность", [1, 4, 7, 13, 17, 20, 23]),
        "surps_anxiety_sensitivity": ("Чувствительность к тревоге", [8, 10, 14, 18, 21]),
        "surps_impulsivity": ("Импульсивность", [2, 5, 11, 15, 22]),
        "surps_sensation_seeking": ("Поиск ощущений", [3, 6, 9, 12, 16, 19]),
    }
    for key, (label, numbers) in surps_subscales.items():
        scales.append(_scale(key, label, _terms("SURPS", numbers), constant=0, aggregation="sum"))

    # Buss-Perry aggression: 3 subscales, plain sum, no reverse items in this instrument.
    bpaq_subscales = {
        "bpaq_physical_aggression": ("Физическая агрессия", list(range(1, 10))),
        "bpaq_anger": ("Гнев", list(range(10, 17))),
        "bpaq_hostility": ("Враждебность", list(range(17, 25))),
    }
    for key, (label, numbers) in bpaq_subscales.items():
        scales.append(_scale(key, label, _terms("BPAQ", numbers), constant=0, aggregation="sum"))

    return scales


def _band(
    minimum: float | None,
    maximum: float | None,
    label: str,
    *,
    is_flagged: bool = False,
    recommendation_text: str | None = None,
) -> dict[str, Any]:
    return {
        "min": minimum,
        "max": maximum,
        "label": label,
        "is_flagged": is_flagged,
        "recommendation_text": recommendation_text,
    }


_PSYCH_SERVICE_CONTACT = (
    "Рекомендуем обратиться в Психологическую службу РУТ (МИИТ): ул. Новосущевская, д. 18, "
    "1 этаж, 109 каб., будни 8:00-20:00, тел. +7 495 274-03-95, e-mail psysupport@rut-miit.ru."
)


def _build_filters() -> list[dict[str, Any]]:
    """Only the scales the source ТЗ gives explicit numeric bands for (§4.2's worked example):
    depression, state/trait anxiety, and all 5 BAT scores. Every other computed scale (academic
    motivation, socio-cultural environment, basic needs, SURPS, aggression) is structurally
    scored but intentionally has no filter yet -- thresholds/wording are still pending RUT
    psychological-service sign-off per the task doc's "Content not yet resolvable" section.
    Only depression's and anxiety's high bands carry `is_flagged`/`recommendation_text`: those
    are the only bands the source example ties to an explicit recommendation sentence. BAT's
    bands are included with their labels only -- the ТЗ's own example does not attach a specific
    recommendation sentence to any individual BAT band."""
    return [
        {
            "result_scale_key": "bdi_total",
            "rules": [
                _band(
                    0,
                    12,
                    "нормальное эмоциональное состояние, достаточный уровень мотивации и жизненного тонуса",
                ),
                _band(
                    13, 17, "умеренное снижение мотивации и жизненного тонуса, умеренное снижение настроения"
                ),
                _band(
                    18,
                    26,
                    "выраженное снижение показателей",
                    is_flagged=True,
                    recommendation_text=f"Может быть полезна помощь психолога. {_PSYCH_SERVICE_CONTACT}",
                ),
                _band(
                    27,
                    60,
                    "сильное снижение настроения, очень низкая мотивация и жизненный тонус",
                    is_flagged=True,
                    recommendation_text=f"Необходима помощь психолога и, возможно, врача-психиатра. {_PSYCH_SERVICE_CONTACT}",
                ),
            ],
        },
        *[
            {
                "result_scale_key": key,
                "rules": [
                    _band(None, 30, "низкий уровень тревожности"),
                    _band(31, 44, "умеренный (нормальный) уровень"),
                    _band(
                        45,
                        None,
                        "высокий уровень тревожности (требует внимания)",
                        is_flagged=True,
                        recommendation_text=_PSYCH_SERVICE_CONTACT,
                    ),
                ],
            }
            for key in ("stai_state", "stai_trait")
        ],
        {
            "result_scale_key": "bat_overall",
            "rules": [
                _band(1.00, 1.50, "низкий уровень"),
                _band(1.51, 2.35, "средний уровень"),
                _band(2.36, 3.17, "высокий уровень"),
                _band(3.18, 5.00, "очень высокий уровень"),
            ],
        },
        {
            "result_scale_key": "bat_exhaustion",
            "rules": [
                _band(1.00, 1.66, "низкий уровень"),
                _band(1.67, 2.99, "средний уровень"),
                _band(3.00, 3.99, "высокий уровень"),
                _band(4.00, 5.00, "очень высокий уровень"),
            ],
        },
        {
            "result_scale_key": "bat_distancing",
            "rules": [
                _band(1.00, 1.00, "низкий уровень"),
                _band(1.01, 2.65, "средний уровень"),
                _band(2.66, 3.99, "высокий уровень"),
                _band(4.00, 5.00, "очень высокий уровень"),
            ],
        },
        {
            "result_scale_key": "bat_cognitive",
            "rules": [
                _band(1.00, 1.66, "низкий уровень"),
                _band(1.67, 2.33, "средний уровень"),
                _band(2.34, 3.32, "высокий уровень"),
                _band(3.33, 5.00, "очень высокий уровень"),
            ],
        },
        {
            "result_scale_key": "bat_emotional",
            "rules": [
                _band(1.00, 1.00, "низкий уровень"),
                _band(1.01, 2.00, "средний уровень"),
                _band(2.01, 3.00, "высокий уровень"),
                _band(3.01, 5.00, "очень высокий уровень"),
            ],
        },
    ]


_RESULT_TEMPLATE = """\
Благодарим Вас за участие в Психологическом мониторинге!

Ниже будут представлены Ваши результаты и их расшифровка.

Депрессивная симптоматика: Ваше значение — {{result:bdi_total.value}}.
Расшифровка: {{result:bdi_total.label}}.
{{#flagged:bdi_total}}{{result:bdi_total.recommendation}}{{/flagged:bdi_total}}

Показатель ситуативной тревожности: Ваше значение — {{result:stai_state.value}}.
Расшифровка: {{result:stai_state.label}}.
{{#flagged:stai_state}}{{result:stai_state.recommendation}}{{/flagged:stai_state}}

Показатель личностной тревожности: Ваше значение — {{result:stai_trait.value}}.
Расшифровка: {{result:stai_trait.label}}.
{{#flagged:stai_trait}}{{result:stai_trait.recommendation}}{{/flagged:stai_trait}}

Учебное выгорание: Ваше значение — {{result:bat_overall.value}} ({{result:bat_overall.label}}).
Истощение: {{result:bat_exhaustion.value}} ({{result:bat_exhaustion.label}}).
Внутреннее дистанцирование: {{result:bat_distancing.value}} ({{result:bat_distancing.label}}).
Когнитивные затруднения: {{result:bat_cognitive.value}} ({{result:bat_cognitive.label}}).
Эмоциональные затруднения: {{result:bat_emotional.value}} ({{result:bat_emotional.label}}).

Все полученные результаты не являются диагнозами и могут меняться в зависимости от множества \
факторов. Если ощущение истощения, эмоционального напряжения или трудностей в учебе сохраняется \
длительное время, может быть полезно обратиться за консультацией к психологу.
"""


def build_rut_spt_schema(source_path: Path | str | None = None) -> dict[str, Any]:
    """Assemble and validate RUT's SPT test schema from the supplied import table plus the
    result-scale formulas/filters encoded above. Raises the same domain validation errors a
    hand-authored schema would if anything doesn't line up (unknown scoring_key reference,
    duplicate key, dependency cycle, ...)."""
    elements = load_rut_spt_elements(source_path or _SOURCE_PATH)
    raw_schema = {
        "elements": elements,
        "result_scales": _build_result_scales(),
        "filters": _build_filters(),
        "result_template": _RESULT_TEMPLATE,
    }
    return validate_test_schema(raw_schema)

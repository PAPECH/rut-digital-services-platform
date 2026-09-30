from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class StatsPeriod(BaseModel):
    date_from: date
    date_to: date


class StatsKpi(BaseModel):
    total_submissions: int

    avg_new_to_work_seconds: int
    avg_work_to_done_seconds: int

    rejected_share: float

    users_total: int
    users_with_submission: int
    conversion_rate: float


class StatsFormItem(BaseModel):
    form_id: int
    name: str
    count: int


class StatsForms(BaseModel):
    all: list[StatsFormItem]
    new_users: list[StatsFormItem]


class StatsActionItem(BaseModel):
    action_type: str
    count: int


class StatsActions(BaseModel):
    mode: str
    items: list[StatsActionItem]


class StatsTicket(BaseModel):
    open: int
    new: int
    closed: int

    avg_response_seconds: int

    ai_answers: int


class StatsTimeseriesItem(BaseModel):
    day: date | None
    count: int


class StatsTicketTimeseriesItem(BaseModel):
    day: date
    new: int
    closed: int


class StatsActionTimeseriesItem(BaseModel):
    day: date
    action_type: str
    count: int


class StatsOverview(BaseModel):
    period: StatsPeriod

    kpi: StatsKpi

    forms: StatsForms

    actions: StatsActions

    tickets: StatsTicket

    timeseries: list[StatsTimeseriesItem]

    tickets_timeseries: list[StatsTicketTimeseriesItem]

    actions_timeseries: list[StatsActionTimeseriesItem]

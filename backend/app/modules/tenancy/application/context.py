from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantContext:
    bot_instance_id: int
    slug: str
    name: str

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnsurePlatformAdminCommand:
    max_user_id: str
    full_name: str

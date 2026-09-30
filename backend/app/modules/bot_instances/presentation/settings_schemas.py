from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    value: str | None = None


class SettingIn(BaseModel):
    value: str | None = None

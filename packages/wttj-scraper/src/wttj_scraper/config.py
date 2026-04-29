from __future__ import annotations

from pathlib import Path
import os

import yaml
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    login_url: str
    matches_url: str
    email_env: str
    password_env: str
    email: str
    password: str


class FiltersConfig(BaseModel):
    location: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    remote: list[str] = Field(default_factory=list)
    contract: list[str] = Field(default_factory=list)
    salary: list[str] = Field(default_factory=list)


class FamilyConfig(BaseModel):
    roles: list[str]


class LimitsConfig(BaseModel):
    max_jobs_per_family: int
    max_pages_per_role: int


class TimingConfig(BaseModel):
    action_delay_seconds: tuple[float, float]
    family_delay_seconds: tuple[float, float]
    detail_delay_seconds: tuple[float, float]


class OutputConfig(BaseModel):
    save_json: bool = True
    save_parquet: bool = True
    include_listing_snapshot: bool = True


class MatchesConfig(BaseModel):
    auth: AuthConfig
    global_filters: FiltersConfig
    families: dict[str, FamilyConfig]
    limits: LimitsConfig
    timing: TimingConfig
    output: OutputConfig


def load_matches_config(path: str | Path) -> MatchesConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    auth_raw = dict(raw["auth"])
    email = os.getenv(auth_raw["email_env"])
    password = os.getenv(auth_raw["password_env"])
    if not email:
        raise ValueError(f"Missing environment variable: {auth_raw['email_env']}")
    if not password:
        raise ValueError(f"Missing environment variable: {auth_raw['password_env']}")
    auth_raw["email"] = email
    auth_raw["password"] = password
    raw["auth"] = auth_raw
    return MatchesConfig.model_validate(raw)

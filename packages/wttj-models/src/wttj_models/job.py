from datetime import datetime, timezone
from pydantic import BaseModel, Field


class JobListing(BaseModel):
    title: str | None
    url: str
    snippet: str | None
    source_category: str | None = None
    location_label: str | None = None


class JobDetail(JobListing):
    job_id: str | None = None
    job_title: str | None = None
    job_url: str | None = None
    source_site: str = "welcometothejungle"
    source: str | None = None
    date_posted_label: str | None = None
    contract_type: str | None = None
    contract_duration_months_min: int | None = None
    contract_duration_months_max: int | None = None
    start_date: str | None = None
    employment_type: str | None = None
    remote_level: str | None = None
    city: str | None = None
    postal_code: str | None = None
    region: str | None = None
    country: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    salary_visible: bool = False
    salary_label: str | None = None
    company_name: str | None = None
    company_size: str | None = None
    company_sectors: list[str] = Field(default_factory=list)
    company_founded_year: int | None = None
    company_avg_age: int | None = None
    company_stage: str | None = None
    company_description: str | None = None
    experience_label: str | None = None
    experience_min_months: int | None = None
    experience_max_months: int | None = None
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    languages_required: list[str] = Field(default_factory=list)
    languages_optional: list[str] = Field(default_factory=list)
    skills_hard: list[str] = Field(default_factory=list)
    skills_soft: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    job_functions: list[str] = Field(default_factory=list)
    page_title: str | None = None
    description_raw: str | None = None
    missions_raw: str | None = None
    profile_raw: str | None = None
    benefits_raw: str | None = None
    text_preview: str | None = None
    error: str | None = None
    parse_version: str = "v2"


class ScrapeResult(BaseModel):
    source: str
    count: int
    jobs: list[JobDetail]
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

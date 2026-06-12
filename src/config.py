from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

_CONFIG_DIR = Path(__file__).parent.parent / "config"

load_dotenv()


@dataclass(frozen=True)
class Keywords:
    structured_sewer_values: list[str]
    description_keywords: list[str]
    negation_patterns: list[str]


@dataclass(frozen=True)
class AppConfig:
    zip_codes: list[str]
    recipients: list[str]
    keywords: Keywords
    # Secrets — may be None in dry-run / CI mock runs
    listings_api_key: str | None
    owner_api_key: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    email_from: str | None


def load_config() -> AppConfig:
    with open(_CONFIG_DIR / "zip_codes.yml") as f:
        zip_data = yaml.safe_load(f)
    with open(_CONFIG_DIR / "recipients.yml") as f:
        rec_data = yaml.safe_load(f)
    with open(_CONFIG_DIR / "keywords.yml") as f:
        kw_data = yaml.safe_load(f)

    return AppConfig(
        zip_codes=zip_data["zip_codes"],
        recipients=rec_data["recipients"],
        keywords=Keywords(
            structured_sewer_values=kw_data["structured_sewer_values"],
            description_keywords=kw_data["description_keywords"],
            negation_patterns=kw_data["negation_patterns"],
        ),
        listings_api_key=os.getenv("LISTINGS_API_KEY"),
        owner_api_key=os.getenv("OWNER_API_KEY"),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        email_from=os.getenv("EMAIL_FROM"),
    )

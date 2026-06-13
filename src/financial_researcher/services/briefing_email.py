"""Send briefing reports via the Resend API."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from financial_researcher.services.briefing_html import briefing_markdown_to_email_html
from financial_researcher.settings import get_email_settings

RESEND_API_URL = "https://api.resend.com/emails"


class BriefingEmailError(RuntimeError):
    """Raised when email delivery is misconfigured or the API call fails."""


def build_email_subject(
    *,
    session: str,
    date_str: str,
    language: str,
    subject_prefix: str = "[Watchlist]",
) -> str:
    prefix = subject_prefix.strip() or "[Watchlist]"
    return f"{prefix} {session.replace('_', ' ').title()} {date_str} ({language})"


def extract_briefing_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _validate_email_settings(settings: dict[str, Any]) -> None:
    if not settings.get("api_key"):
        raise BriefingEmailError(
            "RESEND_API_KEY is not set. Add it to .env (see .env.sample)."
        )
    if not settings.get("from_address"):
        raise BriefingEmailError(
            "BRIEFING_EMAIL_FROM is not set. Use a verified Resend sender "
            "(e.g. Financial Researcher <onboarding@resend.dev> for testing)."
        )
    if not settings.get("to_addresses"):
        raise BriefingEmailError(
            "BRIEFING_EMAIL_TO is not set. Add one or more recipients, "
            "comma-separated."
        )


def send_briefing_email(
    *,
    markdown_text: str,
    markdown_path: Path | None,
    session: str,
    date_str: str,
    language: str,
    settings: dict[str, Any] | None = None,
) -> str:
    """Send the briefing as HTML via Resend. Returns the Resend email id."""
    cfg = settings if settings is not None else get_email_settings()
    _validate_email_settings(cfg)

    fallback_title = build_email_subject(
        session=session,
        date_str=date_str,
        language=language,
        subject_prefix=cfg["subject_prefix"],
    )
    title = extract_briefing_title(markdown_text, fallback_title)
    subject = build_email_subject(
        session=session,
        date_str=date_str,
        language=language,
        subject_prefix=cfg["subject_prefix"],
    )
    html = briefing_markdown_to_email_html(markdown_text, title=title)

    payload: dict[str, Any] = {
        "from": cfg["from_address"],
        "to": cfg["to_addresses"],
        "subject": subject,
        "html": html,
        "text": markdown_text,
    }

    if markdown_path is not None and markdown_path.is_file():
        attachment_bytes = markdown_path.read_bytes()
        payload["attachments"] = [
            {
                "filename": markdown_path.name,
                "content": base64.b64encode(attachment_bytes).decode("ascii"),
            }
        ]

    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason
        raise BriefingEmailError(
            f"Resend API error ({response.status_code}): {detail}"
        )

    data = response.json()
    email_id = data.get("id", "")
    if not email_id:
        raise BriefingEmailError(f"Resend API returned no email id: {data!r}")
    return str(email_id)

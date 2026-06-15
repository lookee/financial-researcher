"""Send briefing reports via the Resend API."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from financial_researcher.paths import briefings_dir
from financial_researcher.services.briefing_html import briefing_markdown_to_email_html
from financial_researcher.services.chart_generator import resolve_chart_markdown_src
from financial_researcher.settings import get_email_settings

RESEND_API_URL = "https://api.resend.com/emails"


def _build_chart_attachments(
    chart_artifacts: list[Any] | None,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Return (Resend attachments, {relative_src: content_id}) for inline charts."""
    attachments: list[dict[str, str]] = []
    src_to_cid: dict[str, str] = {}
    for artifact in chart_artifacts or []:
        path = getattr(artifact, "path", None)
        content_id = getattr(artifact, "content_id", None)
        if path is None or content_id is None or not path.is_file():
            continue
        attachments.append(
            {
                "filename": path.name,
                "content": base64.b64encode(path.read_bytes()).decode("ascii"),
                "content_id": content_id,
                "content_type": "image/png",
            }
        )
        markdown_src = resolve_chart_markdown_src(path, base_dir=briefings_dir())
        src_to_cid[markdown_src] = content_id
    return attachments, src_to_cid


def _inline_chart_images(html: str, src_to_cid: dict[str, str]) -> str:
    """Rewrite <img src="..."> to inline cid: references for email."""
    for src, content_id in src_to_cid.items():
        cid = f"cid:{content_id}"
        html = html.replace(f'src="{src}"', f'src="{cid}"')
        encoded = quote(src, safe="/")
        if encoded != src:
            html = html.replace(f'src="{encoded}"', f'src="{cid}"')
    return html


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
    chart_artifacts: list[Any] | None = None,
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

    chart_attachments, src_to_cid = _build_chart_attachments(chart_artifacts)
    html = _inline_chart_images(html, src_to_cid)

    payload: dict[str, Any] = {
        "from": cfg["from_address"],
        "to": cfg["to_addresses"],
        "subject": subject,
        "html": html,
        "text": markdown_text,
    }

    attachments: list[dict[str, str]] = list(chart_attachments)
    if markdown_path is not None and markdown_path.is_file():
        attachment_bytes = markdown_path.read_bytes()
        attachments.append(
            {
                "filename": markdown_path.name,
                "content": base64.b64encode(attachment_bytes).decode("ascii"),
            }
        )
    if attachments:
        payload["attachments"] = attachments

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

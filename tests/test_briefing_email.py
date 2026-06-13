"""Tests for briefing HTML conversion and Resend email delivery."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from financial_researcher.services.briefing_email import (
    BriefingEmailError,
    build_email_subject,
    send_briefing_email,
)
from financial_researcher.services.briefing_html import briefing_markdown_to_email_html

SAMPLE_MD = """# Milan Watchlist — Close 2026-06-12

**Market mood:** Tech leads.

## Snapshot

| Ref | Ticker | 1D |
|-----|--------|----|
| [1] | SMH.MI | 5.66% |

Read more at [Borsa Italiana](https://www.borsaitaliana.it/).
"""


class TestBriefingHtml:
    def test_renders_table_and_links(self):
        html = briefing_markdown_to_email_html(SAMPLE_MD, title="Test")
        assert "<table" in html
        assert "SMH.MI" in html
        assert 'href="https://www.borsaitaliana.it/"' in html

    def test_wraps_document_with_title(self):
        html = briefing_markdown_to_email_html(SAMPLE_MD, title="Milan Watchlist")
        assert "<!DOCTYPE html>" in html
        assert "Milan Watchlist" in html


class TestBriefingEmail:
    def test_build_email_subject(self):
        subject = build_email_subject(
            session="close",
            date_str="2026-06-12",
            language="Italian",
        )
        assert subject == "[Watchlist] Close 2026-06-12 (Italian)"

    def test_send_requires_api_key(self):
        with pytest.raises(BriefingEmailError, match="RESEND_API_KEY"):
            send_briefing_email(
                markdown_text=SAMPLE_MD,
                markdown_path=None,
                session="close",
                date_str="2026-06-12",
                language="English",
                settings={
                    "api_key": "",
                    "from_address": "Test <a@b.com>",
                    "to_addresses": ["you@example.com"],
                    "subject_prefix": "[Watchlist]",
                    "auto_send": False,
                },
            )

    def test_send_posts_to_resend(self, monkeypatch, tmp_path: Path):
        md_path = tmp_path / "watchlist_2026-06-12_close.md"
        md_path.write_text(SAMPLE_MD, encoding="utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "email_123"}
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr(
            "financial_researcher.services.briefing_email.requests.post",
            mock_post,
        )

        email_id = send_briefing_email(
            markdown_text=SAMPLE_MD,
            markdown_path=md_path,
            session="close",
            date_str="2026-06-12",
            language="English",
            settings={
                "api_key": "re_test",
                "from_address": "Financial Researcher <onboarding@resend.dev>",
                "to_addresses": ["you@example.com"],
                "subject_prefix": "[Watchlist]",
                "auto_send": False,
            },
        )

        assert email_id == "email_123"
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["from"] == "Financial Researcher <onboarding@resend.dev>"
        assert payload["to"] == ["you@example.com"]
        assert payload["subject"] == "[Watchlist] Close 2026-06-12 (English)"
        assert "<table" in payload["html"]
        assert payload["text"] == SAMPLE_MD
        assert payload["attachments"][0]["filename"] == "watchlist_2026-06-12_close.md"

    def test_send_surfaces_resend_errors(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Invalid from address"
        mock_response.reason = "Unprocessable Entity"
        monkeypatch.setattr(
            "financial_researcher.services.briefing_email.requests.post",
            MagicMock(return_value=mock_response),
        )

        with pytest.raises(BriefingEmailError, match="422"):
            send_briefing_email(
                markdown_text=SAMPLE_MD,
                markdown_path=None,
                session="close",
                date_str="2026-06-12",
                language="English",
                settings={
                    "api_key": "re_test",
                    "from_address": "bad@example.com",
                    "to_addresses": ["you@example.com"],
                    "subject_prefix": "[Watchlist]",
                    "auto_send": False,
                },
            )

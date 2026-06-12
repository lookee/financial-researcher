"""Tests for the shared retry helper."""

import json

import pytest
import requests

from financial_researcher.services.retry import is_retryable, with_retries


class TestIsRetryable:
    def test_connection_error_is_retryable(self):
        assert is_retryable(requests.ConnectionError("down")) is True

    def test_http_404_is_not_retryable(self):
        response = requests.Response()
        response.status_code = 404
        exc = requests.HTTPError(response=response)
        assert is_retryable(exc) is False

    def test_http_429_is_retryable(self):
        response = requests.Response()
        response.status_code = 429
        exc = requests.HTTPError(response=response)
        assert is_retryable(exc) is True


class TestWithRetries:
    def test_succeeds_after_transient_failures(self, monkeypatch):
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise requests.Timeout("slow")
            return "ok"

        monkeypatch.setattr("financial_researcher.services.retry.time.sleep", lambda _: None)
        assert with_retries(flaky, attempts=3, base_delay=0.01) == "ok"
        assert calls["n"] == 3

    def test_gives_up_after_max_attempts(self, monkeypatch):
        monkeypatch.setattr("financial_researcher.services.retry.time.sleep", lambda _: None)

        def always_fails() -> None:
            raise requests.ConnectionError("still down")

        with pytest.raises(requests.ConnectionError):
            with_retries(always_fails, attempts=3, base_delay=0.01)

    def test_does_not_retry_non_transient_errors(self, monkeypatch):
        calls = {"n": 0}

        def bad_request() -> None:
            calls["n"] += 1
            response = requests.Response()
            response.status_code = 400
            raise requests.HTTPError(response=response)

        with pytest.raises(requests.HTTPError):
            with_retries(bad_request, attempts=3, base_delay=0.01)
        assert calls["n"] == 1

    def test_json_decode_error_is_retried(self, monkeypatch):
        calls = {"n": 0}

        def flaky_json() -> dict:
            calls["n"] += 1
            if calls["n"] == 1:
                raise json.JSONDecodeError("bad", "", 0)
            return {"ok": True}

        monkeypatch.setattr("financial_researcher.services.retry.time.sleep", lambda _: None)
        assert with_retries(flaky_json, attempts=2, base_delay=0.01) == {"ok": True}

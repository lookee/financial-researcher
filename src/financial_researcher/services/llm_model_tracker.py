"""Track LiteLLM/OpenRouter resolved models per agent during a briefing run."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

_ACTIVE_AGENT = threading.local()
_COMPLETION_PATCHED = False
_ORIGINAL_COMPLETION: Any = None


class RunModelTracker:
    """Collects distinct resolved model ids per agent, in first-seen order."""

    def __init__(self) -> None:
        self._by_agent: dict[str, list[str]] = {}

    def reset(self) -> None:
        self._by_agent.clear()

    def record(self, agent: str, model: str) -> None:
        normalized = model.strip()
        if not agent or not normalized:
            return
        seen = self._by_agent.setdefault(agent, [])
        if normalized not in seen:
            seen.append(normalized)

    def snapshot(self) -> dict[str, list[str]]:
        return {agent: list(models) for agent, models in self._by_agent.items()}


_RUN_TRACKER = RunModelTracker()


def get_run_model_tracker() -> RunModelTracker:
    return _RUN_TRACKER


def reset_run_model_tracker() -> None:
    _RUN_TRACKER.reset()


def _set_active_agent(agent: str) -> None:
    _ACTIVE_AGENT.key = agent


def _clear_active_agent() -> None:
    if hasattr(_ACTIVE_AGENT, "key"):
        del _ACTIVE_AGENT.key


def _active_agent() -> str | None:
    return getattr(_ACTIVE_AGENT, "key", None)


def extract_resolved_model(response_obj: Any) -> str | None:
    """Read the concrete model slug from a LiteLLM/OpenRouter response."""
    if response_obj is None:
        return None
    if isinstance(response_obj, dict):
        model = response_obj.get("model")
    else:
        model = getattr(response_obj, "model", None)
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None


def _record_agent_model(agent: str | None, response_obj: Any) -> None:
    model = extract_resolved_model(response_obj)
    if agent and model:
        _RUN_TRACKER.record(agent, model)


def _record_active_agent_model(response_obj: Any) -> None:
    _record_agent_model(_active_agent(), response_obj)


def _wrap_stream(agent: str | None, stream: Any) -> Iterator[Any]:
    last_chunk: Any = None
    for chunk in stream:
        last_chunk = chunk
        yield chunk
    if agent:
        _record_agent_model(agent, last_chunk)


def _patch_litellm_completion() -> None:
    """Patch litellm.completion so tracking survives CrewAI callback resets."""
    global _COMPLETION_PATCHED, _ORIGINAL_COMPLETION
    if _COMPLETION_PATCHED:
        return

    import litellm

    _ORIGINAL_COMPLETION = litellm.completion

    def completion(*args: Any, **kwargs: Any) -> Any:
        agent = _active_agent()
        response = _ORIGINAL_COMPLETION(*args, **kwargs)
        if kwargs.get("stream"):
            return _wrap_stream(agent, response)
        _record_agent_model(agent, response)
        return response

    litellm.completion = completion
    _COMPLETION_PATCHED = True


def ensure_llm_model_tracker_installed() -> None:
    """Install the LiteLLM completion patch when litellm is available."""
    try:
        _patch_litellm_completion()
    except ImportError:
        # CrewAI-free unit CI has no litellm; tracking still works via thread-local agent tags.
        return


def tracked_llm_call(agent_key: str, call_fn: Any, /, *args: Any, **kwargs: Any) -> Any:
    """Run an LLM call while tagging LiteLLM responses with the active agent."""
    ensure_llm_model_tracker_installed()
    _set_active_agent(agent_key)
    try:
        return call_fn(*args, **kwargs)
    finally:
        _clear_active_agent()


def build_tracked_llm(*, agent_key: str, **llm_kwargs: Any) -> Any:
    """Return a CrewAI LLM subclass that records resolved models for one agent."""
    from crewai import LLM

    ensure_llm_model_tracker_installed()

    class TrackedLLM(LLM):
        fr_agent_key: str

        def __init__(self, *, agent_key: str, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.fr_agent_key = agent_key

        def call(
            self,
            messages,
            tools=None,
            callbacks=None,
            available_functions=None,
        ):
            return tracked_llm_call(
                self.fr_agent_key,
                super().call,
                messages,
                tools=tools,
                callbacks=callbacks,
                available_functions=available_functions,
            )

    return TrackedLLM(agent_key=agent_key, **llm_kwargs)

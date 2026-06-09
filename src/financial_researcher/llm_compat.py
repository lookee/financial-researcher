"""LiteLLM/CrewAI compatibility shims.

OpenAI gpt-5.x rejects the `stop` parameter, but LiteLLM still advertises it as
supported — CrewAI then sends stop sequences and the API returns 400.
"""

from crewai import LLM

_NO_STOP_MODEL_MARKERS = ("gpt-5", "o1", "o3")

_orig_prepare = LLM._prepare_completion_params
_orig_supports_stop = LLM.supports_stop_words


def _model_rejects_stop(model: str) -> bool:
    lowered = model.lower()
    return any(marker in lowered for marker in _NO_STOP_MODEL_MARKERS)


def _prepare_completion_params(self, messages, tools=None):
    params = _orig_prepare(self, messages, tools)
    if _model_rejects_stop(self.model):
        params.pop("stop", None)
    return params


def _supports_stop_words(self) -> bool:
    if _model_rejects_stop(self.model):
        return False
    return _orig_supports_stop(self)


def apply_llm_compat_patches() -> None:
    LLM._prepare_completion_params = _prepare_completion_params
    LLM.supports_stop_words = _supports_stop_words


apply_llm_compat_patches()

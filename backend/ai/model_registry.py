"""Unified multi-provider LLM caller — OpenAI, Anthropic (Claude), and
Google (Gemini) behind one call(model, messages, **kwargs) interface,
dispatched by model-name prefix, plus embed() for text embeddings.

Standalone by design: no hard DB dependency (db_session is optional,
used only for cost logging), nothing imported from server.py. Does NOT
replace or touch server.py's existing OpenAI usage (responses_text(),
the streaming /api/chat path, embed_texts()) — those use the Responses
API and are already working, untouched. This module's _call_openai uses
Chat Completions (client.chat.completions.create) instead, because its
native "messages: list of {role, content}" shape matches this module's
own interface directly, with no translation needed for OpenAI or
Claude — only Gemini needs real translation (see _call_gemini).

Anthropic and Google SDKs are lazily imported inside _call_claude/
_call_gemini, not at module load — both packages ARE installed (anthropic,
google-genai), but no ANTHROPIC_API_KEY/GOOGLE_API_KEY is configured in
this environment, so neither has a real successful call to test against.
What IS verified for real, with real (fake-key) network calls that reach
each provider's actual servers and fail on auth as expected: request
shape (Gemini's contents/config translation genuinely gets accepted, not
rejected client-side) and each SDK's real exception shape (.status_code
vs .code, which values mean "don't retry this") — see
_is_non_retryable's docstring. _call_openai and embed() get full,
successful real round-trips, since OPENAI_API_KEY is genuinely configured.

Uses google-genai (google.genai), not the older google-generativeai —
that package is fully deprecated by Google as of this writing ("no
longer receiving updates or bug fixes"), confirmed by actually importing
it and reading the FutureWarning it now emits on import. Building new
code against it would mean starting on a dead end.

Cost: estimate_cost()/log() are CostLedger's job (backend/ai/cost_ledger.py),
not this module's — see that file's docstring for why it's a new, narrow
ledger rather than a reuse of AIUsageLedger/UsageLog (discussed and
decided explicitly, not a default).
"""
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, declarative_base

from .cost_ledger import CostLedger, create_cost_ledger_model
from observability import record_ai_call

logger = logging.getLogger(__name__)

_Base = declarative_base()
CostLedgerEntry = create_cost_ledger_model(_Base)

# Routing prefixes for OpenAI — not just "gpt-": the o-series (o1, o1-mini,
# o3-mini, ...) are OpenAI models too, with their own prefix family.
_OPENAI_PREFIXES = ("gpt-", "o1", "o3", "o4")


class ModelError(Exception):
    """Raised for any provider-call failure — after retries are
    exhausted, an unrecognized model prefix, a missing SDK, or a missing
    API key. Callers only need to catch this one type."""

    def __init__(self, message, *, provider=None, model=None, attempts=None, cause=None):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.attempts = attempts
        self.cause = cause


class ModelRegistry:
    MAX_ATTEMPTS = 3

    def __init__(self, db_session: Optional[Session] = None):
        from openai import OpenAI
        self._openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        # Claude/Gemini: no client built here — held as keys only, real
        # clients constructed lazily per call, so a missing SDK or key
        # can't break __init__ for an app that only ever uses OpenAI.
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._google_key = os.environ.get("GOOGLE_API_KEY", "")

        self.db_session = db_session
        # Fallback-of-the-fallback (only matters if DEFAULT_MODEL is
        # entirely unset) kept to a model with confident pricing in
        # CostLedger.PRICING, same reasoning as server.py's own
        # DEFAULT_MODEL default.
        self.default_model = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
        self.embed_model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
        self._cost_ledger = CostLedger(CostLedgerEntry)

    # ------------------------------------------------------------ public
    def call(self, model: str, messages: List[Dict], fallback_models: Optional[list] = None,
             **kwargs) -> Dict[str, Any]:
        """fallback_models isn't in the original method list — added
        because the brief asks for a caller "with automatic fallbacks"
        without pinning down a mechanism; this is the minimal one:
        opt-in list, no default chain, no config file."""
        user_id = kwargs.pop("user_id", None)
        candidates = [model] + list(fallback_models or [])
        errors = []

        for candidate in candidates:
            try:
                result = self._dispatch(candidate, messages, **kwargs)
                self._attach_cost_and_log(result, user_id)
                return result
            except ModelError as exc:
                errors.append(exc)
                logger.warning("model %s failed, trying next candidate: %s", candidate, exc)

        if len(errors) == 1:
            raise errors[0]
        raise ModelError(
            f"all {len(candidates)} model candidate(s) failed: "
            f"{'; '.join(str(e) for e in errors)}",
            model=model, attempts=len(candidates))

    def embed(self, text: str, model: Optional[str] = None, user_id: Optional[int] = None) -> List[float]:
        """user_id isn't in the original signature either — added
        because "log cost as action='embedding'" is otherwise
        unactionable (no identity to log it against), same reasoning as
        call()'s user_id kwarg."""
        model = model or self.embed_model
        vector, tokens = self._call_with_retry(self._embed_openai, "openai", model, text)
        record_ai_call(model, prompt_tokens=tokens)

        cost = self._cost_ledger.estimate_cost(model, tokens, 0)
        if user_id is not None and self.db_session is not None:
            self._log_cost_safely(user_id=user_id, model=model, prompt_tokens=tokens,
                                  completion_tokens=0, total_tokens=tokens,
                                  cost=cost, action="embedding")
        return vector

    # ------------------------------------------------------------ routing
    def _dispatch(self, model: str, messages: list, **kwargs) -> dict:
        if model.startswith(_OPENAI_PREFIXES):
            fn, provider = self._call_openai, "openai"
        elif model.startswith("claude-"):
            fn, provider = self._call_claude, "anthropic"
        elif model.startswith("gemini-"):
            fn, provider = self._call_gemini, "google"
        else:
            raise ModelError(f"unrecognized model prefix: {model!r}", model=model)
        return self._call_with_retry(fn, provider, model, messages, **kwargs)

    def _call_with_retry(self, fn, provider: str, model: str, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                return fn(model, *args, **kwargs)
            except (ValueError, TypeError):
                raise   # malformed request / bad args — retrying won't help
            except Exception as exc:
                if self._is_non_retryable(exc):
                    raise ModelError(
                        f"{provider} call for {model!r} failed (not retried): {exc}",
                        provider=provider, model=model, attempts=attempt, cause=exc) from exc
                last_exc = exc
                logger.warning("attempt %d/%d for %s (%s) failed: %s",
                               attempt, self.MAX_ATTEMPTS, model, provider, exc)
                if attempt < self.MAX_ATTEMPTS:
                    self._sleep(attempt * 2)
        raise ModelError(
            f"{provider} call for {model!r} failed after {self.MAX_ATTEMPTS} attempts: {last_exc}",
            provider=provider, model=model, attempts=self.MAX_ATTEMPTS, cause=last_exc)

    @staticmethod
    def _is_non_retryable(exc: Exception) -> bool:
        """Invalid API key / bad auth and unknown-model errors won't
        succeed on retry — everything else (rate limits, timeouts,
        5xx/transient errors) is assumed retryable. Matched by status
        code when the SDK exposes one (both openai and anthropic
        exceptions do), not by string-matching messages. google-genai is
        the odd one out — it has no .status_code at all, only .code, and
        uses 400 (INVALID_ARGUMENT) for a bad API key rather than 401 —
        verified against the real SDK, not assumed; 400 also matches the
        spec's own "malformed request" case for the other two."""
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        return status in (400, 401, 403, 404)

    @staticmethod
    def _sleep(seconds):
        import time
        time.sleep(seconds)

    @staticmethod
    def _split_system_message(messages: list):
        """OpenAI puts a system prompt inside `messages` (role="system");
        Anthropic and Gemini both take it as a separate top-level param.
        Pulled out once, shared by both non-OpenAI callers."""
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        chat_messages = [m for m in messages if m.get("role") != "system"]
        return ("\n".join(system_parts) if system_parts else None), chat_messages

    def _attach_cost_and_log(self, result: dict, user_id) -> None:
        record_ai_call(result["model"], result["prompt_tokens"], result["completion_tokens"])
        cost = self._cost_ledger.estimate_cost(
            result["model"], result["prompt_tokens"], result["completion_tokens"])
        result["cost"] = cost
        if user_id is not None and self.db_session is not None:
            self._log_cost_safely(
                user_id=user_id, model=result["model"], prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"], total_tokens=result["total_tokens"],
                cost=cost, action="chat")

    def _log_cost_safely(self, **kwargs):
        # Best-effort: a logging failure must never take down an
        # otherwise-successful call, same reasoning as the upload
        # route's quota-increment logging (backend/upload/routes.py).
        try:
            self._cost_ledger.log(self.db_session, **kwargs)
        except Exception:
            logger.warning("cost logging failed", exc_info=True)

    # ------------------------------------------------------------ providers
    def _call_openai(self, model: str, messages: list, **kwargs) -> dict:
        if kwargs.pop("stream", False):
            return self._call_openai_streaming(model, messages, **kwargs)
        resp = self._openai.chat.completions.create(model=model, messages=messages, **kwargs)
        choice = resp.choices[0]
        usage = resp.usage
        return {
            "content": choice.message.content,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "model": resp.model,
            "finish_reason": choice.finish_reason,
        }

    def _call_openai_streaming(self, model: str, messages: list, **kwargs) -> dict:
        """Consumes the stream internally and returns the same unified
        dict every other call returns — a deliberate simplification, not
        a live generator handed to the caller. The task's own contract
        ("Return in the unified format") is one dict shape everywhere;
        exposing a raw stream would break that for every caller that
        doesn't specifically ask for it. Upgrade path: a separate
        call_streaming() that yields chunks, if a real caller needs
        token-by-token delivery."""
        kwargs.setdefault("stream_options", {"include_usage": True})
        stream = self._openai.chat.completions.create(
            model=model, messages=messages, stream=True, **kwargs)

        content_parts, finish_reason, usage, resp_model = [], None, None, model
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content_parts.append(delta.content)
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if getattr(chunk, "model", None):
                resp_model = chunk.model

        return {
            "content": "".join(content_parts),
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "model": resp_model,
            "finish_reason": finish_reason,
        }

    def _call_claude(self, model: str, messages: list, **kwargs) -> dict:
        if not self._anthropic_key:
            raise ModelError("ANTHROPIC_API_KEY not configured", provider="anthropic", model=model)
        try:
            import anthropic
        except ImportError as exc:
            raise ModelError("anthropic package not installed (pip install anthropic)",
                            provider="anthropic", model=model) from exc

        client = anthropic.Anthropic(api_key=self._anthropic_key)
        system, chat_messages = self._split_system_message(messages)
        kwargs.setdefault("max_tokens", 1024)   # Anthropic requires this, unlike OpenAI/Gemini
        resp = client.messages.create(
            model=model, messages=chat_messages,
            **({"system": system} if system else {}), **kwargs)

        content = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text")
        return {
            "content": content,
            "prompt_tokens": resp.usage.input_tokens,
            "completion_tokens": resp.usage.output_tokens,
            "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
            "model": resp.model,
            "finish_reason": resp.stop_reason,
        }

    def _call_gemini(self, model: str, messages: list, **kwargs) -> dict:
        if not self._google_key:
            raise ModelError("GOOGLE_API_KEY not configured", provider="google", model=model)
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ModelError("google-genai package not installed (pip install google-genai)",
                            provider="google", model=model) from exc

        client = genai.Client(api_key=self._google_key)
        system, chat_messages = self._split_system_message(messages)
        # Gemini has no "assistant" role — it's "model" — and no plain
        # {role, content} shape, so this is a real translation, unlike
        # the pass-through OpenAI/Anthropic get. Verified against the
        # real SDK: this dict shape is accepted (reaches the network,
        # doesn't raise client-side).
        contents = [
            {"role": "model" if m.get("role") == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in chat_messages
        ]

        # Generation params go inside a config object here, not as flat
        # kwargs — confirmed against the real SDK (a direct temperature=
        # kwarg raises TypeError). Translates this registry's unified
        # kwargs (temperature/max_tokens/top_p); anything else passed
        # through as-is, forward-compatible rather than an exhaustive list.
        config_kwargs = dict(kwargs)
        if system:
            config_kwargs["system_instruction"] = system
        if "max_tokens" in config_kwargs:
            config_kwargs["max_output_tokens"] = config_kwargs.pop("max_tokens")
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        resp = client.models.generate_content(model=model, contents=contents, config=config)

        usage = getattr(resp, "usage_metadata", None)
        prompt_tokens = usage.prompt_token_count if usage else 0
        completion_tokens = usage.candidates_token_count if usage else 0
        return {
            "content": resp.text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.total_token_count if usage else prompt_tokens + completion_tokens,
            "model": model,
            "finish_reason": str(resp.candidates[0].finish_reason) if resp.candidates else None,
        }

    # ------------------------------------------------------------ embeddings
    def _embed_openai(self, model: str, text: str, **kwargs):
        resp = self._openai.embeddings.create(model=model, input=text, **kwargs)
        tokens = resp.usage.total_tokens if resp.usage else 0
        return resp.data[0].embedding, tokens

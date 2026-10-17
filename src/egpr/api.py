"""Small audited chat API adapter; every network result goes through Ledger.

No automatic retries, model substitution, semantic cache, or billing claims.
Model aliases and returned model IDs are both retained in the raw receipts.
"""
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
import shlex
import ssl
import time
import urllib.error
import urllib.request

from .ledger import Ledger, Receipt, Request, money
from .schema import canonical


ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "together": "https://api.together.ai/v1/chat/completions",
}
KEY_NAMES = {"openai": "OPENAI_API_KEY", "together": "TOGETHER_API_KEY"}


class ModelResponseError(ValueError):
    """The received result remains cached, including invalid/truncated outputs."""


def load_credentials(path: Path | None = None) -> dict[str, str]:
    values = {k: os.environ[k] for k in KEY_NAMES.values() if os.environ.get(k)}
    if path:
        # Parse assignments only. Never source a shell script or expand commands.
        for line in path.read_text().splitlines():
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == "export":
                parts = parts[1:]
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    if key in KEY_NAMES.values():
                        values.setdefault(key, value)
    return values


def tls_context():
    configured = os.environ.get("EGPR_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if configured:
        return ssl.create_default_context(cafile=configured)
    # Standalone Python on RHEL may look for a Debian/OpenSSL certificate path.
    rhel = Path("/etc/pki/tls/certs/ca-bundle.crt")
    return ssl.create_default_context(cafile=str(rhel) if rhel.is_file() else None)


@dataclass(frozen=True)
class Tariff:
    input_per_million: str
    output_per_million: str
    cached_input_per_million: str | None = None
    cache_write_per_million: str | None = None
    long_context_threshold: int | None = None
    long_input_multiplier: str = "1"
    long_output_multiplier: str = "1"
    source_url: str = ""
    checked_at: str = ""

    def __post_init__(self):
        for name in ("input_per_million", "output_per_million", "cached_input_per_million",
                     "cache_write_per_million", "long_input_multiplier", "long_output_multiplier"):
            value = getattr(self, name)
            if value is not None:
                money(value)

    def rates(self, prompt_tokens):
        long = self.long_context_threshold is not None and prompt_tokens > self.long_context_threshold
        return (money(self.long_input_multiplier) if long else Decimal(1),
                money(self.long_output_multiplier) if long else Decimal(1))

    def estimate(self, usage):
        """Conservative estimate if provider omits cache-write token details.

        Reasoning tokens are already included in completion_tokens. Cached input
        is a provider discount, different from zero-new-call local response reuse.
        """
        if not isinstance(usage, dict):
            return None, None
        prompt, output = usage.get("prompt_tokens"), usage.get("completion_tokens")
        details = usage.get("prompt_tokens_details") or {}
        if not isinstance(details, dict):
            return None, None
        cached = details.get("cached_tokens", usage.get("cached_tokens", 0))
        if any(type(n) is not int or n < 0 for n in (prompt, output, cached)) or cached > prompt:
            return None, None
        im, om = self.rates(prompt)
        regular = money(self.input_per_million)
        uncached = max(regular, money(self.cache_write_per_million or self.input_per_million))
        read = money(self.cached_input_per_million or str(uncached))
        estimate = ((prompt - cached) * uncached * im + cached * read * im
                    + output * money(self.output_per_million) * om) / 1_000_000
        logical = (prompt * regular * im + output * money(self.output_per_million) * om) / 1_000_000
        return str(estimate), str(logical)

    def reserve(self, context_tokens, output_tokens):
        # Reserve the full documented context, not an unverified chars/token
        # heuristic. Output has a provider-enforced cap. This deliberately
        # over-reserves each sequential call; usage releases the unused amount.
        im, om = self.rates(context_tokens)
        rate = max(money(self.input_per_million),
                   money(self.cache_write_per_million or self.input_per_million))
        return str((context_tokens * rate * im
                    + output_tokens * money(self.output_per_million) * om) / 1_000_000)


def payload(request: Request):
    if request.provider not in ENDPOINTS or request.endpoint != ENDPOINTS[request.provider]:
        raise ValueError("Provider/endpoint is not explicitly configured")
    generation = dict(request.generation)
    if len(generation) != len(request.generation):
        raise ValueError("Duplicate generation parameters")
    if set(generation) & {"model", "messages", "tools", "response_format", "stream", "n"}:
        raise ValueError("Generation parameters may not override request identity")
    caps = [generation[k] for k in ("max_tokens", "max_completion_tokens") if k in generation]
    if len(caps) != 1 or type(caps[0]) is not int or caps[0] <= 0:
        raise ValueError("Exactly one positive output-token cap is required")
    if any(not isinstance(m.get("content"), str) for m in request.messages):
        raise ValueError("This adapter supports text-only messages")
    body = {"model": request.model_snapshot, "messages": list(request.messages),
            "response_format": request.response_format, "stream": False, "n": 1, **generation}
    if request.tools:
        body["tools"] = list(request.tools)
    return body


class ChatBackend:
    def __init__(self, credentials, tariff: Tariff, *, timeout=45, opener=None):
        self.credentials, self.tariff, self.timeout = credentials, tariff, timeout
        self.opener = opener or urllib.request.urlopen

    def __call__(self, request: Request):
        body = payload(request)
        key = self.credentials.get(KEY_NAMES[request.provider])
        if not key:
            raise ValueError("Missing credential: " + KEY_NAMES[request.provider])
        req = urllib.request.Request(request.endpoint, data=canonical(body).encode(), headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json",
            "User-Agent": "EGPR-research/0.2"})
        start = time.perf_counter()
        try:
            response = self.opener(req, context=tls_context(), timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
            request_id = response.headers.get("x-request-id") or response.headers.get("x-amzn-requestid")
        # JSON extraction happens after persisting the raw transport envelope.
        envelope = {"http_status": status, "raw_body": raw,
                    "elapsed_seconds": time.perf_counter() - start}
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        usage = parsed.get("usage")
        estimate, logical = self.tariff.estimate(usage)
        blocked = status in {401, 402, 403, 429}
        return Receipt(envelope, billed_usd=None, logical_uncached_usd=logical,
                       provider_request_id=request_id or parsed.get("id"), usage=usage,
                       estimated_usd=estimate, cost_basis="usage_times_frozen_tariff_upper_estimate",
                       access_blocked=blocked)


def parse_completion(envelope):
    if envelope.get("http_status") != 200:
        raise ModelResponseError("HTTP status " + str(envelope.get("http_status")))
    try:
        body = json.loads(envelope["raw_body"])
        choice = body["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
            raise ModelResponseError("Refused, truncated, or unfinished completion")
        content = choice["message"]["content"]
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ModelResponseError("Duplicate JSON key")
                result[key] = value
            return result
        def reject_constant(_):
            raise ModelResponseError("Non-finite JSON number")
        value = json.loads(content, object_pairs_hook=unique, parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise ModelResponseError("Expected a JSON object")
        return value
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ModelResponseError("Invalid completion structure") from exc


def call_json(ledger: Ledger, request: Request, backend, *, maximum_usd):
    envelope = ledger.run(request, backend, paid=True, maximum_usd=maximum_usd)
    return parse_completion(envelope)

"""Provider-agnostic LLM client for semantic extraction.

Bedrock-first (correction 6): the default backend is Amazon Bedrock via the
``converse`` API, so the hackathon runs on Bedrock with no RunPod dependency.
The same interface also targets Anthropic-direct, OpenAI, and any
OpenAI-compatible server (vLLM/local), selected by ``WBM_LLM_BACKEND``.

A ``MockLLMClient`` returns canned structured output so the extraction and
reconciliation logic is fully testable offline (no cloud, no keys).
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional


# Cheap "normal extraction" default and the escalation model, both on Bedrock.
DEFAULT_BEDROCK_MODEL = os.environ.get("WBM_BEDROCK_MODEL", "anthropic.claude-3-5-haiku-20241022-v1:0")
DEFAULT_BEDROCK_ESCALATION_MODEL = os.environ.get(
    "WBM_BEDROCK_ESCALATION_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)


def _extract_json(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                pass
    return {"error": "bad_json", "raw": raw[:1200]}


class LLMClient:
    """Interface: return parsed JSON for a (system, user, optional image) prompt."""

    name = "base"
    model = "unknown"

    def complete_json(
        self,
        system: str,
        user: str,
        image_data_url: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError


class BedrockClient(LLMClient):
    """Amazon Bedrock via the Converse API (boto3). Default backend."""

    name = "bedrock"

    def __init__(self, model: Optional[str] = None, region: Optional[str] = None):
        self.model = model or DEFAULT_BEDROCK_MODEL
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        import boto3  # lazy: only needed for a live Bedrock call

        client = boto3.client("bedrock-runtime", region_name=self.region)
        content: list[dict] = []
        if image_data_url:
            fmt, data_b64 = _split_data_url(image_data_url)
            import base64
            content.append({"image": {"format": fmt, "source": {"bytes": base64.b64decode(data_b64)}}})
        content.append({"text": user})
        resp = client.converse(
            modelId=self.model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": content}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        parts = resp["output"]["message"]["content"]
        text = "".join(p.get("text", "") for p in parts)
        return _extract_json(text)


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.environ.get("WBM_MODEL", "claude-3-5-haiku-20241022")

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        import anthropic  # lazy

        client = anthropic.Anthropic()
        content: list[dict] = []
        if image_data_url:
            media_type, data_b64 = _split_media_url(image_data_url)
            content.append({"type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": data_b64}})
        content.append({"type": "text", "text": user})
        resp = client.messages.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": content}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        return _extract_json(text)


class OpenAICompatibleClient(LLMClient):
    """OpenAI or any OpenAI-compatible server (vLLM / local). Not RunPod-pinned."""

    name = "openai_compatible"

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("WBM_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("WBM_LLM_API_KEY", "") or os.environ.get("OPENAI_KEY", "")
        self.model = model or os.environ.get("WBM_LLM_MODEL", "gpt-4.1-mini")

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        import requests  # lazy

        user_content: list[dict] = []
        if image_data_url:
            user_content.append({"type": "image_url", "image_url": {"url": image_data_url}})
        user_content.append({"type": "text", "text": user})
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user_content}]},
            timeout=int(os.environ.get("WBM_LLM_TIMEOUT", "120")),
        )
        resp.raise_for_status()
        return _extract_json(resp.json()["choices"][0]["message"]["content"])


class MockLLMClient(LLMClient):
    """Returns canned structured output. For offline tests / the benchmark."""

    name = "mock"
    model = "mock"

    def __init__(self, responder: Callable[[str, str], dict] | dict):
        self._responder = responder

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        if callable(self._responder):
            return self._responder(system, user)
        return dict(self._responder)


def get_client(backend: Optional[str] = None, escalation: bool = False) -> LLMClient:
    backend = (backend or os.environ.get("WBM_LLM_BACKEND", "bedrock")).lower()
    if backend == "bedrock":
        return BedrockClient(model=DEFAULT_BEDROCK_ESCALATION_MODEL if escalation else None)
    if backend == "anthropic":
        return AnthropicClient()
    if backend in ("openai", "openai_compatible"):
        return OpenAICompatibleClient()
    if backend == "mock":
        return MockLLMClient({"error": "mock not configured"})
    raise ValueError(f"unknown WBM_LLM_BACKEND: {backend}")


def _split_data_url(data_url: str) -> tuple[str, str]:
    # data:image/png;base64,XXXX -> ("png", "XXXX")
    header, b64 = data_url.split(",", 1)
    media = header.split(";")[0].replace("data:image/", "")
    return media, b64


def _split_media_url(data_url: str) -> tuple[str, str]:
    header, b64 = data_url.split(",", 1)
    media_type = header.replace("data:", "").split(";")[0]
    return media_type, b64

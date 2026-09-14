"""Provider-agnostic LLM + embedding access.

Design goal: the whole system runs deterministically with **no API key** (stub mode),
and transparently upgrades to real OpenAI reasoning when a key is present. The agent's
numeric decisions never depend on the LLM (see app/agent/nodes.py) -- the LLM only
produces natural-language rationale -- so behaviour is identical and testable either way.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

from app.config import get_settings

settings = get_settings()


# --------------------------------------------------------------------------- #
# Chat models
# --------------------------------------------------------------------------- #
class StubChat:
    """Deterministic 'LLM'. Echoes a structured rationale built from the prompt."""

    provider = "stub"

    def complete(self, system: str, user: str) -> str:
        # We simply surface the structured facts the caller already computed.
        # The caller passes a compact rationale request; we return it verbatim-ish.
        return user.strip()


class OpenAIChat:
    provider = "openai"

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    def call_tools(self, messages: list, tools: list) -> dict:
        """One turn of a tool-calling loop. Returns {content, tool_calls:[{id,name,arguments}]}."""
        import json as _json

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
        )
        msg = resp.choices[0].message
        tool_calls = []
        for tc in (msg.tool_calls or []):
            try:
                args = _json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
        return {"content": msg.content or "", "tool_calls": tool_calls}


def get_chat() -> "StubChat | OpenAIChat":
    if settings.use_real_llm:
        try:
            return OpenAIChat(settings.llm_model, settings.openai_api_key)
        except Exception:
            return StubChat()
    return StubChat()


# --------------------------------------------------------------------------- #
# Embeddings (for RAG)
# --------------------------------------------------------------------------- #
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class StubEmbedder:
    """Deterministic bag-of-hashed-tokens embedding. No network needed.

    Good enough for keyword-semantic retrieval over a small SOP corpus.
    """

    dim = 256
    provider = "stub"

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _TOKEN_RE.findall(text.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class OpenAIEmbedder:
    dim = 1536
    provider = "openai"

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]


def get_embedder() -> "StubEmbedder | OpenAIEmbedder":
    if settings.use_real_llm:
        try:
            return OpenAIEmbedder(settings.embedding_model, settings.openai_api_key)
        except Exception:
            return StubEmbedder()
    return StubEmbedder()

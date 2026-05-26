"""LLM-based feature extractor for token metadata.

Uses Claude Sonnet to score each token snapshot on signals that aren't
captured by tabular features:
    legit_score          0-1: does this look like a legitimate meme launch vs scam
    theme                short string: 'dog', 'political', 'AI', 'cat', etc.
    name_quality         0-1: name + symbol look professional
    sentiment_emoji      -1..+1: vibe of the name+symbol
    coordination_signal  0-1: does the metadata pattern-match coordinated scam launches

Cached: each (mint, name, symbol, uri-hash) triple is scored once and cached
to JSONL. Re-running on the same token doesn't re-call the API.

Cost discipline:
    Claude Sonnet 4.6 pricing ~$3/$15 per M input/output tokens. Each token
    scoring is ~200 input + 50 output tokens ≈ $0.001 per token. At 100 new
    tokens evaluated per day = $0.10/day. Negligible.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from helios.ops import get_logger

log = get_logger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-6"

LLM_CACHE_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "llm_token_scores.jsonl"


@dataclass(frozen=True, slots=True)
class TokenLLMFeatures:
    legit_score: float           # 0-1
    theme: str                   # short tag
    name_quality: float          # 0-1
    sentiment_emoji: float       # -1..1
    coordination_signal: float   # 0-1; higher = more scam-shape
    raw_response_excerpt: str    # for audit

    @property
    def is_legit(self) -> bool:
        return self.legit_score >= 0.5 and self.coordination_signal <= 0.5


class LLMTokenScorer:
    """Score Solana token metadata via Claude Sonnet. Cached + bounded."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        client: Optional[httpx.AsyncClient] = None,
        cache_path: Path = LLM_CACHE_PATH,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self.cache_path = cache_path
        self._cache: dict[str, TokenLLMFeatures] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        with self.cache_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    self._cache[rec["cache_key"]] = TokenLLMFeatures(
                        legit_score=rec["legit_score"], theme=rec["theme"],
                        name_quality=rec["name_quality"],
                        sentiment_emoji=rec["sentiment_emoji"],
                        coordination_signal=rec["coordination_signal"],
                        raw_response_excerpt=rec.get("raw_response_excerpt", ""),
                    )
                except (json.JSONDecodeError, KeyError):
                    continue

    def _cache_key(self, mint: str, name: str, symbol: str, uri: str = "") -> str:
        s = f"{mint}|{name}|{symbol}|{uri}"
        return hashlib.sha256(s.encode()).hexdigest()[:24]

    async def score(self, mint: str, name: str, symbol: str, uri: str = "") -> TokenLLMFeatures | None:
        """Return cached features, or call the LLM. Returns None if no API key
        or the call fails — caller decides what to do without these features."""
        key = self._cache_key(mint, name, symbol, uri)
        if key in self._cache:
            return self._cache[key]
        if not self.api_key:
            log.debug("llm_disabled_no_key")
            return None

        prompt = (
            "Score this Solana memecoin's token metadata on 5 axes. Be concise.\n"
            f"\nName: {name}\nSymbol: {symbol}\nMint: {mint}\n"
            "\nReturn a single JSON object with these exact keys (no commentary, no code fences):\n"
            "{\n"
            '  "legit_score": <0-1, higher = looks like a real meme launch vs scam>,\n'
            '  "theme": <one short tag, e.g. "dog", "AI", "political", "absurd", "cat">,\n'
            '  "name_quality": <0-1, higher = name and symbol look professional/coherent>,\n'
            '  "sentiment_emoji": <-1 to 1, the vibe>,\n'
            '  "coordination_signal": <0-1, higher = pattern-matches coordinated scam launches '
            '(e.g. unicode tricks, repetitive themes from same era, "moon" / "elon" / "1000x" patterns)>\n'
            "}"
        )

        try:
            resp = await self._client.post(
                ANTHROPIC_API_URL,
                json={
                    "model": self.model,
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                },
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("llm_call_failed", error=str(e))
            return None

        body = resp.json()
        text = ""
        for block in body.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        try:
            # Strip possible markdown fences; find the JSON object
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("no JSON object in response")
            parsed = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("llm_parse_failed", error=str(e), excerpt=text[:200])
            return None

        features = TokenLLMFeatures(
            legit_score=float(parsed.get("legit_score", 0.0)),
            theme=str(parsed.get("theme", "unknown")),
            name_quality=float(parsed.get("name_quality", 0.0)),
            sentiment_emoji=float(parsed.get("sentiment_emoji", 0.0)),
            coordination_signal=float(parsed.get("coordination_signal", 1.0)),  # safe default
            raw_response_excerpt=text[:500],
        )
        self._cache[key] = features
        # Persist to cache file
        parent = self.cache_path.parent
        target = parent.resolve() if parent.is_symlink() else parent
        try:
            target.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "cache_key": key, "mint": mint, "name": name, "symbol": symbol,
                **{k: getattr(features, k) for k in ("legit_score", "theme", "name_quality",
                                                     "sentiment_emoji", "coordination_signal",
                                                     "raw_response_excerpt")},
            }) + "\n")
        return features

    async def close(self) -> None:
        await self._client.aclose()

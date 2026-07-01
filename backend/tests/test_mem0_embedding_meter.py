"""Task 17: code-level metering for the mem0 embedder.

mem0's ``embed()`` returns only the vector (no tokens/cost) and, on a self-hosted
model, bypasses LiteLLM entirely — so those calls land in NEITHER
``LiteLLM_SpendLogs`` NOR ``token_usage_events``. The meter wraps ``embed`` to
record a best-effort usage row without changing the vector mem0 gets back.
"""

from __future__ import annotations

from decimal import Decimal

from backend.app.memory import embedding_meter as em
from backend.app.services.llm_cost import extract_cost, extract_usage

# ── estimate_tokens ──────────────────────────────────────────────────────────


def test_estimate_tokens_chars_over_four_ceil() -> None:
    assert em.estimate_tokens("abcd") == 1  # 4 chars / 4
    assert em.estimate_tokens("abcde") == 2  # 5 chars → ceil(5/4)
    assert em.estimate_tokens("") == 0
    assert em.estimate_tokens(None) == 0


def test_estimate_tokens_handles_batch_list() -> None:
    # mem0 can embed a batch — sum the characters across items.
    assert em.estimate_tokens(["ab", "cd"]) == 1  # 4 chars total
    assert em.estimate_tokens(["abcd", "efgh"]) == 2  # 8 chars total


# ── build_embedding_response (compatible with extract_usage/extract_cost) ─────


def test_build_response_unpriced_by_default() -> None:
    """Default rate 0 (self-hosted) → tokens counted, cost 0, and extract_cost
    reports a real 0 (Decimal("0"), not None) so record_llm_usage marks it
    priced=False rather than falling back to LiteLLM pricing."""
    resp = em.build_embedding_response("abcdefgh", model="local-embed", cost_per_token=0.0)

    usage = extract_usage(resp)
    assert usage["prompt_tokens"] == 2  # 8 chars / 4
    assert usage["completion_tokens"] == 0
    assert usage["model"] == "local-embed"

    assert extract_cost(resp) == Decimal("0")


def test_build_response_priced_when_rate_positive() -> None:
    resp = em.build_embedding_response("abcdefgh", model="gemini-embedding", cost_per_token=0.001)
    # 2 tokens * 0.001 = 0.002 > 0 → priced
    assert extract_cost(resp) == Decimal("0.002")


# ── wrap_embedding_model ─────────────────────────────────────────────────────


class _FakeEmbedder:
    def __init__(self, vector):
        self._vector = vector
        self.calls = []

    def embed(self, text, memory_action=None):
        self.calls.append((text, memory_action))
        return self._vector


def test_wrap_passthrough_and_meters_with_workspace(monkeypatch) -> None:
    """The wrapped embed returns the SAME vector (mem0 correctness untouched) and
    submits exactly one metering coroutine, attributed to the current workspace."""
    submitted = []

    def _fake_submit(coro):
        submitted.append(coro)
        coro.close()  # don't leave an un-awaited coroutine

    monkeypatch.setattr(em, "submit_metering", _fake_submit)

    emb = _FakeEmbedder([0.1, 0.2, 0.3])
    token = em.current_workspace.set("acme")
    try:
        wrapped = em.wrap_embedding_model(
            emb,
            get_workspace=em.current_workspace.get,
            model_name="local-embed",
            cost_per_token=0.0,
        )
        assert wrapped is True
        out = emb.embed("show revenue by region", memory_action="search")
    finally:
        em.current_workspace.reset(token)

    assert out == [0.1, 0.2, 0.3]  # passthrough
    assert len(submitted) == 1  # one metering call


def test_wrap_skips_metering_without_workspace(monkeypatch) -> None:
    submitted = []
    monkeypatch.setattr(em, "submit_metering", lambda coro: (submitted.append(coro), coro.close()))

    emb = _FakeEmbedder([0.9])
    em.wrap_embedding_model(
        emb, get_workspace=lambda: None, model_name="local-embed", cost_per_token=0.0
    )
    out = emb.embed("no tenant in context")

    assert out == [0.9]
    assert submitted == []  # no workspace → nothing metered


def test_wrap_metering_failure_never_breaks_embed(monkeypatch) -> None:
    def _boom(_coro):
        raise RuntimeError("metering down")

    monkeypatch.setattr(em, "submit_metering", _boom)

    emb = _FakeEmbedder([1.0, 2.0])
    em.wrap_embedding_model(
        emb, get_workspace=lambda: "acme", model_name="local-embed", cost_per_token=0.0
    )
    # Metering blew up, but embed must still return the vector.
    assert emb.embed("x") == [1.0, 2.0]


def test_wrap_is_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(em, "submit_metering", lambda coro: coro.close())
    emb = _FakeEmbedder([0.0])
    assert (
        em.wrap_embedding_model(
            emb, get_workspace=lambda: "acme", model_name="m", cost_per_token=0.0
        )
        is True
    )
    # Re-wrapping the same embedder is a no-op (singleton re-init guard).
    assert (
        em.wrap_embedding_model(
            emb, get_workspace=lambda: "acme", model_name="m", cost_per_token=0.0
        )
        is False
    )

"""
08 — LangChain callback handler.

SentinelCallbackHandler records every LangChain LLM, chain, and
tool call as a sovereign decision trace. Zero changes to the agent
logic. Optional dependency:

    pip install sentinel-kernel[langchain]

To keep this example self-contained and API-key-free, it uses a
minimal fake BaseCallbackHandler injected into sys.modules before
importing the integration. A real deployment imports from
`langchain_core.callbacks` normally.

Run:
    python examples/08_langchain_agent.py
"""

from __future__ import annotations

import importlib
import sys
import types
from uuid import uuid4

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


def _install_fake_langchain() -> None:
    pkg = types.ModuleType("langchain_core")
    callbacks = types.ModuleType("langchain_core.callbacks")

    class _Base:
        pass

    callbacks.BaseCallbackHandler = _Base  # type: ignore[attr-defined]
    pkg.callbacks = callbacks  # type: ignore[attr-defined]
    sys.modules["langchain_core"] = pkg
    sys.modules["langchain_core.callbacks"] = callbacks


def main() -> None:
    _install_fake_langchain()
    import sentinel.integrations.langchain as lc_mod
    importlib.reload(lc_mod)

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="langchain-demo",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )
    handler = lc_mod.SentinelCallbackHandler(sentinel=sentinel)

    # Simulate three LLM calls arriving via the LangChain callback interface
    class _Gen:
        def __init__(self, text: str) -> None:
            self.text = text

    class _Result:
        def __init__(self, text: str) -> None:
            self.generations = [[_Gen(text)]]

    prompts_and_responses = [
        ("Classify this document: 'public notice of works'",      "UNCLASSIFIED"),
        ("Classify this document: 'internal strategy memo'",      "RESTRICTED"),
        ("Classify this document: 'contract negotiation draft'",  "CONFIDENTIAL"),
    ]
    for prompt, response in prompts_and_responses:
        run_id = uuid4()
        handler.on_llm_start(
            serialized={"name": "mock-classifier-v1"},
            prompts=[prompt],
            run_id=run_id,
        )
        handler.on_llm_end(_Result(response), run_id=run_id)

    traces = sentinel.query(limit=10)
    print(f"Recorded {len(traces)} LangChain LLM decision(s):")
    for t in traces:
        assert t.output
        out_text = (t.output.get("generations") or [""])[0]
        print(f"  {t.model_name}  → {out_text}")
    print(f"\nSovereign scope : {sentinel.sovereign_scope}")
    print(f"Data residency  : {sentinel.data_residency.value}")


if __name__ == "__main__":
    main()

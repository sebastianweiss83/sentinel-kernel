#!/usr/bin/env python3
"""
Sovereignty check — run in CI to verify no US-owned dependencies
have been introduced into the critical path.

This is the manifesto as code.
"""

import importlib
import inspect
import sys

# Packages with US-incorporated parent companies
# that would introduce CLOUD Act exposure if in the critical path
US_OWNED_PACKAGES = {
    "boto3": "Amazon (AWS)",
    "botocore": "Amazon (AWS)",
    "azure": "Microsoft",
    "google.cloud": "Alphabet (Google)",
    "anthropic": "Anthropic PBC",
    "openai": "OpenAI",
    "langsmith": "LangChain Inc.",
    "helicone": "Helicone Inc.",
}

CRITICAL_PATH_MODULES = [
    "sentinel.core.tracer",
    "sentinel.core.trace",
    "sentinel.policy.evaluator",
    "sentinel.storage.base",
    "sentinel.storage.sqlite",
    "sentinel.storage.filesystem",
]

def check_critical_path():
    violations = []

    for module_name in CRITICAL_PATH_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            print(f"WARNING: Could not import {module_name}")
            continue

        source = inspect.getsource(module)

        for pkg, owner in US_OWNED_PACKAGES.items():
            if pkg in source:
                violations.append(
                    f"VIOLATION: {module_name} imports {pkg} (owned by {owner})"
                )

    if violations:
        print("\nSOVEREIGNTY CHECK FAILED")
        print("=" * 50)
        for v in violations:
            print(f"  {v}")
        print("\nUS-owned dependencies in the critical path create CLOUD Act exposure.")
        print("Move these imports to optional integrations or remove them.")
        sys.exit(1)
    else:
        print("Sovereignty check passed — no US-owned deps in critical path.")


if __name__ == "__main__":
    check_critical_path()

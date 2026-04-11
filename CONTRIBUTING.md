# Contributing to Sentinel

Sentinel is an open infrastructure project. Contributions are welcome
from individuals, research institutions, and organisations.

## Before you start

Read [docs/sovereignty.md](docs/sovereignty.md) to understand what
sovereignty means in this project. Every contribution is evaluated
against the three sovereignty tests:

1. No US CLOUD Act exposure in the critical path.
2. Air-gapped must always work.
3. Apache 2.0 permanently.

## Getting started

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -q
python examples/smoke_test.py
```

All tests should pass. If they don't, open an issue before proceeding.

> **Note on editable installs and console scripts.** If you pull
> changes that modify `[project.scripts]` in `pyproject.toml` —
> for example adding a new `sentinel` subcommand — you must re-run
> `pip install -e .` to refresh the entry-point registration. An
> unrefreshed venv will have a stale `sentinel` script on PATH
> that does not match the source tree. Similarly, when bumping
> the package version in a local venv, re-run the editable
> install to keep `pip show sentinel-kernel` in sync.

## What we need

- **Storage backends** — implementations of the `StorageBackend`
  protocol for additional databases
- **Framework integrations** — LangChain, LangGraph, Haystack,
  AutoGen callback handlers
- **Policy helpers** — utilities for common Rego patterns in
  regulated industries
- **Documentation** — deployment guides for specific environments

## Pull request process

1. One PR per change. Small, focused PRs merge faster.
2. New features need tests. See "Adding a new integration" below.
3. Schema changes need an RFC. Open a GitHub Discussion first.
4. Every integration must include a **sovereignty posture statement**.
5. The sovereignty CI checks must pass.

---

## Sovereignty posture statement

Every PR that adds or modifies a dependency, integration, or
infrastructure component **must** include a sovereignty posture
statement in the PR description. Use this template:

```markdown
## Sovereignty posture
- Framework/package: [name] by [company] ([jurisdiction])
- CLOUD Act exposure: [yes / no / conditional]
- Air-gap capable: [yes / no]
- Runtime network calls: [none / optional / required]
- Critical path: [yes / no]
- Test coverage: [N tests added]
- Sovereign alternatives evaluated: [list or "none relevant"]
```

This is non-negotiable. A PR without a sovereignty posture statement
will be closed until one is added. The template is short because the
thinking should be done before writing code, not after.

---

## Adding a new integration

Integrations live in `sentinel/integrations/`. Use the LangChain
integration (`sentinel/integrations/langchain.py`) as your reference.

### Step 1 — sovereignty check

Before writing any code, fill in the posture statement. If the
framework is US-incorporated **and** makes runtime network calls,
it cannot live in the critical path. It **can** live as an optional
integration guarded by `ImportError`.

### Step 2 — create the module

Put your integration in `sentinel/integrations/<name>.py`. Start
with the module docstring — document the sovereignty posture
inline so anyone reading the file sees it first.

### Step 3 — guard the imports

At module top:

```python
from __future__ import annotations

try:
    import your_framework  # type: ignore
except ImportError as exc:
    raise ImportError(
        "Install with: pip3 install sentinel-kernel[your-framework]"
    ) from exc
```

### Step 4 — expose a callback or adapter

Record a trace on every framework event you care about. Always read
`sovereign_scope` and `data_residency` from the Sentinel instance —
never hardcode them.

### Step 5 — add the optional extra

In `pyproject.toml`:

```toml
[project.optional-dependencies]
your-framework = ["your-framework>=X.Y"]
```

### Step 6 — write the five mandatory tests

Every integration needs these five tests (template in
`tests/test_integration_langchain.py`):

1. **Happy path** — normal call records a trace.
2. **Offline mode** — works without network connectivity.
3. **Policy DENY** — a blocked call is recorded with the policy rule.
4. **Missing-dep error** — `ImportError` raised with a helpful message
   when the optional dep is not installed.
5. **Sovereignty metadata flow-through** — `sovereign_scope` and
   `data_residency` propagate from the Sentinel instance to the trace.

### Step 7 — document in docs/integration-guide.md

Add a section describing when to use the integration and its
sovereignty posture. A user should be able to decide in 30 seconds
whether it is safe for their deployment context.

---

## Adding packages to the jurisdiction database

The `PACKAGE_KNOWLEDGE` map in `sentinel/scanner/knowledge.py` is the
single source of truth for package-level sovereignty classification.
PRs that extend it are welcome.

### Data structure

```python
"package-name": PackageKnowledge(
    parent_company="Legal Entity Name",
    jurisdiction="EU" | "US" | "UK" | "Neutral" | "Unknown",
    cloud_act_exposure=True | False,
    typically_critical_path=True | False,
    notes="One-sentence context",
),
```

### Research checklist — before opening the PR

- [ ] Verified the parent company's legal incorporation (not just HQ).
- [ ] Checked whether the package makes runtime network calls in its
      default configuration.
- [ ] Identified at least one EU-sovereign alternative if one exists
      (add to `EU_ALTERNATIVES`).
- [ ] Checked that the normalised name is not already in the map.

### PR requirements

- Cite one primary source for each non-obvious classification
  (company registry, SEC filing, annual report, or official website).
- If the jurisdiction is ambiguous (e.g. "EU corporate entity but
  uses US-owned cloud"), use `jurisdiction="Unknown"` and explain
  in `notes`. Conservative is better than wrong.
- Add a test to `tests/test_scanner.py` if the entry is for a
  particularly important package or edge case.

---

## RFC process

Significant changes to the trace schema, storage interface, or
sovereignty assertions require an RFC:

1. Open a GitHub Discussion with the RFC template.
2. 14-day comment period.
3. Maintainer decision recorded in the Discussion.
4. If accepted: implement and reference the Discussion in the PR.

See [RFC-001](docs/rfcs/RFC-001-sovereignty-manifest.md) as an example.

---

## Code style

```bash
ruff check sentinel/ tests/ scripts/ examples/ demo/
ruff format .
mypy sentinel/ --ignore-missing-imports
pytest tests/ -q
python examples/smoke_test.py
```

All five must pass before a PR is ready for review.

---

## Security disclosure

**Do not open public issues for security vulnerabilities.**

Email: **security@swentures.com**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix if known

We will acknowledge within 48 hours and aim to resolve within 30 days.
See [SECURITY.md](SECURITY.md) for the full disclosure policy.

---

## Licence

By contributing, you agree that your contributions will be licensed
under Apache 2.0. No CLA. No relicensing rights granted. Forever.

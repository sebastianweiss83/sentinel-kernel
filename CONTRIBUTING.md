# Contributing to Sentinel

Sentinel is an open infrastructure project. Contributions are welcome from individuals, research institutions, and organisations.

## Before you start

Read [docs/sovereignty.md](docs/sovereignty.md) to understand what sovereignty means in this project. Every contribution is evaluated against the three sovereignty tests.

## Getting started

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel
pip install -e ".[dev]"
pytest
```

All 71 tests should pass. If they don't, open an issue before proceeding.

## What we need

- **Storage backends** — implementations of the `StorageBackend` protocol for additional databases
- **Framework integrations** — LangChain, LangGraph, AutoGen callback handlers
- **Policy helpers** — utilities for common Rego patterns in regulated industries
- **Documentation** — deployment guides for specific environments

## Pull request process

1. One PR per change. Small, focused PRs merge faster.
2. New features need tests. The five mandatory tests are in [docs/integration-guide.md](docs/integration-guide.md).
3. Schema changes need an RFC. Open a GitHub Discussion first.
4. Every integration must include a sovereignty posture statement.
5. The sovereignty CI checks must pass.

## RFC process

Significant changes to the trace schema, storage interface, or sovereignty assertions require an RFC:

1. Open a GitHub Discussion with the RFC template
2. 14-day comment period
3. Maintainer decision recorded in the Discussion
4. If accepted: implement and reference the Discussion in the PR

## Code style

```bash
ruff check .
ruff format .
mypy sentinel/ --ignore-missing-imports
```

## Licence

By contributing, you agree that your contributions will be licensed under Apache 2.0. No CLA. No relicensing rights granted.

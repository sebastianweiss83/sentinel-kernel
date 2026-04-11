## Summary
Brief description of what this PR does.

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] New integration
- [ ] Documentation
- [ ] Tests
- [ ] Refactor

## Sovereignty posture (for new integrations/dependencies)
- New dependency: [name]
- Company/jurisdiction: [e.g. deepset GmbH / DE]
- CLOUD Act exposure: [yes/no]
- Air-gap capable: [yes/no]

## Checklist
- [ ] Tests added/updated
- [ ] All tests passing: `pytest tests/ -q`
- [ ] Smoke test passing: `python examples/smoke_test.py`
- [ ] Ruff clean: `ruff check sentinel/ tests/`
- [ ] Mypy clean: `mypy sentinel/ --ignore-missing-imports`
- [ ] Sovereignty check: `python scripts/check_sovereignty.py`
- [ ] CHANGELOG.md updated
- [ ] No external URLs in any HTML files
- [ ] No named partners or customers in any public file

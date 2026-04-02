# Contributing to Sentinel

Contributions are welcome from individuals, research institutions,
and organisations.

---

## Getting started

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Run the test suite: `pytest`
5. Open a pull request

**First contribution?** Look for issues labelled
[`good first issue`](../../issues?q=label%3A%22good+first+issue%22).

---

## Code of conduct

Be respectful, constructive, and professional. Sentinel is built by
a diverse community across industries, institutions, and countries.
Contributions are evaluated on their technical merit.

---

## Pull request requirements

Every PR must:

1. **Pass all existing tests** — no regressions.
2. **Include tests for new functionality** — see test requirements below.
3. **Document sovereignty posture** — if your change introduces a dependency,
   network call, or storage path change, answer the sovereignty checklist
   in your PR description.

### Sovereignty checklist (for PRs that add dependencies or network calls)

- [ ] Who is the parent company of the dependency?
- [ ] Is it US-incorporated and subject to the CLOUD Act?
- [ ] Does it make network calls at runtime?
- [ ] Does it work fully offline?

If the dependency is US-owned and makes network calls: it cannot be in the
critical path. It may be offered as an optional, clearly-labelled integration.

### Test requirements

Every new feature must include at minimum:

1. Happy path test
2. Offline test (local storage, zero network)
3. Policy DENY test (DENY recorded with rule name)
4. Override test (second linked trace entry, original untouched)
5. EU AI Act fields test (all mandatory fields present)

Coverage targets: core trace emission 95%+, storage interface 90%+,
integrations 80%+.

---

## Integration contributions

Adding a new framework or model provider integration? Read
[`docs/integration-guide.md`](docs/integration-guide.md) first.

Every integration must:

- Document its sovereignty posture
- Work offline or clearly label which features require network
- Include a quickstart example under 30 lines
- Pass the standard integration test suite

---

## RFC process

Significant changes to the following require an RFC before implementation:

- Trace schema (mandatory fields, field semantics)
- Storage interface
- Policy evaluation contract
- Sovereignty assertions

### How to open an RFC

1. Create a document at `docs/rfcs/RFC-[NNN]-[title].md`
2. Open a GitHub Discussion linking your RFC
3. A 14-day comment period follows
4. Maintainers vote to accept or reject
5. The decision and rationale are permanently recorded in the Discussion

### What does not require an RFC

- Bug fixes
- New optional trace fields
- New storage backend implementations
- New integration modules
- Documentation improvements
- Test additions

---

## Design partner issues

If your organisation has a deployment context — regulated industry, classified
environment, public sector — that tests Sentinel's architecture, open an issue
on GitHub to discuss design partner status.

---

## Community

- **GitHub Discussions:** For RFCs, architecture questions, and design partner conversations
- Community channels TBD

---

## License

By contributing to Sentinel, you agree that your contributions will be
licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the
full licence text.

No Contributor License Agreement (CLA) is required. No contribution grants
any party the right to relicence this software.

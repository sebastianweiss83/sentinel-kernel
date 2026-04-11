# Releasing sentinel-kernel

Everything needed to cut a `sentinel-kernel` release, from the
three-command happy path to the PyPI trusted-publisher setup and the
failures you will hit if anything drifts.

The release is fully automated via GitHub Actions with OIDC. There
are no tokens in the repo, no manual uploads, and no `twine` on a
developer's laptop. If the three commands below do not produce a PyPI
release in two minutes, something structural is broken — see
[Troubleshooting](#troubleshooting).

---

## One-time setup (already done — do not repeat)

This configuration is in place and does not need to be re-done for
every release. It is documented here as the single source of truth
so that it can be rebuilt in an hour if someone has to rebuild the
project from scratch.

### PyPI trusted publisher

- URL: https://pypi.org/manage/project/sentinel-kernel/settings/publishing/
- Owner: `sebastianweiss83`
- Repository name: `sentinel-kernel`
- Workflow filename: `release.yml`
- Environment name: `release`

### GitHub environment "release"

- URL: https://github.com/sebastianweiss83/sentinel-kernel/settings/environments
- Name: `release`
- No required reviewers, no wait timer (add these later if
  publishing permissions need to be gated).
- No secrets — this uses OIDC, not a token.

### Release workflow

Lives at `.github/workflows/release.yml`. Triggered by tags matching
`v*`. Builds with `python -m build` and publishes using
`pypa/gh-action-pypi-publish@release/v1` with `id-token: write`.

---

## Every release — three commands

Once you have a clean working tree with version and CHANGELOG
updated (see the checklist below):

```bash
git commit -am "chore: vX.Y.Z"
git tag vX.Y.Z
git push origin vX.Y.Z
```

GitHub Actions publishes to PyPI automatically. Watch it at
https://github.com/sebastianweiss83/sentinel-kernel/actions.
Typical time: ~2 minutes from `git push` to
`pip3 install sentinel-kernel==X.Y.Z` working.

> The workflow only runs on **tag pushes**, not on the main-branch
> push. If you forget to push the tag the release will not happen.
> `git push origin main && git push origin vX.Y.Z` are both safe.

---

## Before tagging — checklist

Run this list in order. Every item must be ticked before you tag.

- [ ] Version bumped in `pyproject.toml`
- [ ] Version bumped in `sentinel/__init__.py` (`__version__`)
- [ ] `CHANGELOG.md` updated with the new section (keep the
      `[Unreleased]` header above it)
- [ ] `pytest tests/ -q` → all green
- [ ] `python examples/smoke_test.py` → `ALL 40 STEPS PASSED`
- [ ] `python scripts/check_sovereignty.py` → passes
- [ ] `ruff check sentinel/ tests/ scripts/ examples/` → no errors
- [ ] `CLAUDE_MEGA_PROMPT.md` "Current state" and "Roadmap" sections
      updated to the new version
- [ ] `git status` shows only the intended version / CHANGELOG /
      documentation diff
- [ ] Working tree is on `main` and up to date with `origin/main`

After the release has landed on PyPI:

- [ ] `gh release create vX.Y.Z --title "vX.Y.Z — …" --notes "…"` to
      attach release notes on GitHub
- [ ] If the repo description, homepage, or topics changed, run
      `gh repo edit` to keep metadata in sync

---

## Semantic versioning

The project follows [SemVer](https://semver.org/). In this codebase
that means:

- **PATCH** (`1.0.x`) — bug fixes, coverage improvements, docs,
  cleanup, non-breaking refactors. No public API changes.
- **MINOR** (`1.x.0`) — new features, new optional extras, new
  integration modules, new CLI subcommands. Backwards compatible.
- **MAJOR** (`x.0.0`) — breaking changes to the public API, the
  trace schema, or the three invariants. Requires an RFC (see
  `docs/rfcs/`) before merging.

Schema changes to `DecisionTrace` are a special case: optional field
additions are MINOR; field removal, rename, or a new required field
is MAJOR and requires an RFC.

---

## Troubleshooting

### `invalid-publisher` from the PyPI step

The GitHub environment `release` is missing or misconfigured. Go to
Settings → Environments → New environment and create an environment
named exactly `release`. The workflow refuses to run without it.

### `403 Forbidden` on upload

The version you are trying to publish already exists on PyPI. PyPI
refuses overwrites by policy. Bump the patch version, update
`CHANGELOG.md`, commit, re-tag with the new number, and push again.

If you published a broken release, yank it on PyPI
(`pypi.org/manage/project/sentinel-kernel/releases/`) and release
the next patch. Never reuse a version number.

### Workflow runs but no release on PyPI

Check the workflow logs at
https://github.com/sebastianweiss83/sentinel-kernel/actions. Common
causes: `python -m build` failing because of a syntax error in
`pyproject.toml`, or the trusted-publisher claim being rejected
because the workflow filename is not `release.yml` in the
PyPI configuration.

### Tag pushed but no workflow triggered

The workflow is configured with `on: push: tags: ["v*"]`. Tags that
do not start with `v` (for example `1.0.0` without the `v`) will not
trigger it. Delete the tag (`git tag -d 1.0.0` and
`git push --delete origin 1.0.0`) and re-tag with the correct name.

### Tag points at the wrong commit

Delete and recreate the tag before the release has actually been
published:

```bash
git tag -d vX.Y.Z
git push --delete origin vX.Y.Z
git tag vX.Y.Z <correct-sha>
git push origin vX.Y.Z
```

Do not attempt this after a successful PyPI upload — PyPI will
refuse the re-upload and the release on PyPI will be inconsistent
with the tag in git.

### Smoke test fails with `ruff check passes` at step 39

A file was committed without being formatted. Run
`ruff check --fix sentinel/ tests/ scripts/ examples/`, inspect the
diff, commit the fixes, and re-run the smoke test before tagging.

---

## After the release — Claude Code continuity

Every release is also the moment to update `CLAUDE_MEGA_PROMPT.md`
so the next Claude Code session (which has no memory of the one
before it) sees the current version, current test count, and
current roadmap. The file is the contract between one session and
the next — let it drift and future work starts from a wrong map.

The three-command flow above does not update that file. Keep the
update in the same commit as the version bump, not the tag — the
tag is immutable, but the doc needs to move forward.

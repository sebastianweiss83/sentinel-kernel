# v3.4.2 Ed25519 Default Activation — Implementation Report

## Outcome

**SUCCESS.** Fresh `pip install sentinel-kernel==3.4.2` on a clean venv
now produces `signature_algorithm="Ed25519"` and a real
`Ed25519:<base64>` signature on the default `Sentinel()` trace path.

## Context: why v3.4.2 and not v3.4.1

Phase 1 baseline check discovered v3.4.1 was already tagged and on
PyPI with the `Ed25519Signer.from_default_key()` classmethod and the
`Sentinel.__init__` `_DEFAULT` sentinel wiring both already present in
source. But the reality test that the spec was written to fix
**still failed** on v3.4.1:

```
signature_algorithm: None
signature present: False
AssertionError: FAIL: algorithm is None, expected Ed25519
```

Root cause: `pyproject.toml:44` declared `dependencies = []` (zero core
deps). `cryptography>=42.0` lived only in the optional `[ed25519]`,
`[pades]`, `[pdf]`, and `[dev]` extras. On a default
`pip install sentinel-kernel`, the `cryptography` import failed, the
guard at `ed25519_signer.py:30` set `_HAS_CRYPTOGRAPHY=False`,
`from_default_key()` returned `None` at line 98, and traces shipped
unsigned.

Fix: move `cryptography>=42.0` into core `dependencies`. Retain the
`[ed25519]` extra as a compatibility alias. Ship as v3.4.2 because
v3.4.1 was already immutable on PyPI.

## End-to-end reality test — v3.4.2 from PyPI

```
$ cd /tmp && rm -rf sentinel-v342-test
$ python3 -m venv sentinel-v342-test
$ source sentinel-v342-test/bin/activate
$ pip install sentinel-kernel==3.4.2    # fresh, no extras

$ rm -rf ~/.sentinel ./sentinel-traces.db
$ python << 'PYEOF'
from sentinel import Sentinel
import os, shutil, cryptography
print(f"cryptography installed: {cryptography.__version__}")

s = Sentinel()
@s.trace
def test(x): return {"r": x}
test("hello")

t = s.query()[0]
assert t.signature_algorithm == "Ed25519"
assert t.signature is not None
print(f"SUCCESS: algorithm={t.signature_algorithm}, "
      f"sig_preview={str(t.signature)[:40]}")

keypath = os.path.expanduser('~/.sentinel/ed25519.key')
assert os.path.exists(keypath)
print(f"key persisted at {keypath} "
      f"mode=0o{oct(os.stat(keypath).st_mode)[-3:]}")
PYEOF

cryptography installed: 46.0.7
SUCCESS: algorithm=Ed25519, sig_preview=Ed25519:WkgoeS7CoC0soJUDGDRepbPfhYiATIQj
key persisted at /Users/sebastianweiss/.sentinel/ed25519.key mode=0o600
```

- Default `Sentinel()` activates Ed25519 signing with no explicit args.
- Signature format is the documented `Ed25519:<base64>` envelope.
- Key auto-generated on first use at `~/.sentinel/ed25519.key`,
  permissions `0o600`.

## Files changed

```
 CHANGELOG.md         | 41 +++++++++++++++++++++++++++++++++++++++++
 docs/performance.md  |  2 +-
 pyproject.toml       | 23 +++++++++++++++++------
 sentinel/__init__.py |  2 +-
 4 files changed, 60 insertions(+), 8 deletions(-)
```

No source code in `sentinel/crypto/` or `sentinel/core/` needed to
change — the v3.4.1 Python code was already correct. Only the
package metadata was wrong.

## Test results

- `pytest` (repo dev venv): **911 passed, 5 skipped, 100% coverage**,
  4.89s. No regressions from the dep change.
- Quickstart smoke test (CI, `examples/smoke_test.py`):
  **42/42 steps pass** including step 42 ("No stale version claims
  in docs") after bumping `docs/performance.md` from
  `(v3.4.1, 2026-04-21)` → `(v3.4.2, 2026-04-22)`.
- CI on main (`gh run 24749479916`): all 9 jobs green — Test 3.11,
  Test 3.12, Quickstart smoke, Lint & type, Sovereignty, Air-gapped,
  Manifesto, Sync-all, Pages deploy.
- Release workflow on tag v3.4.2 (`gh run 24749701949`): PyPI publish
  via trusted publisher + digital attestations, **success**.

## PyPI status

```
$ python3 -m pip index versions sentinel-kernel
sentinel-kernel (3.4.2)
Available versions: 3.4.2, 3.4.1, 3.4.0, ...
```

- **v3.4.2 published: yes**
- **pip install sentinel-kernel==3.4.2 succeeds: yes**
- **Fresh venv reality test: PASS** (signature_algorithm="Ed25519",
  signature present)

## Outstanding: yank v3.4.1

Authorization granted for "A+C" (ship v3.4.2 *and* yank v3.4.1), but
the yank could not run from the local CLI because the repo uses
PyPI trusted-publisher OIDC for release — no long-lived API token
exists locally and no `~/.pypirc` is configured. Two paths for you:

1. **Web UI, one click** (recommended):
   https://pypi.org/manage/project/sentinel-kernel/release/3.4.1/ →
   "Options" → "Yank".
   Use this reason (paste verbatim): *"v3.4.1 had a packaging bug:
   cryptography dependency was in optional [ed25519] extra instead
   of core dependencies, causing Ed25519 default signing to silently
   no-op on fresh installs. Fixed in v3.4.2."*

2. **Generate a user token and run `twine yank`** — more work than
   the one-click path; not worth it for a single yank.

Until yanked, `pip install sentinel-kernel` still resolves to v3.4.2
(the newer version wins), but anyone who pinned `==3.4.1` will keep
getting the broken version. The yank makes that resolver refuse
without `--pre` / explicit ignore.

## What you should verify in the morning

1. Run the exact reality test above on a brand-new venv. Confirm
   `algorithm=Ed25519` and a signature string.
2. One-click yank v3.4.1 at the URL above.
3. If confirmed: v3.4.2 is ready for the upcoming design-partner
   review — the "Ed25519 signatures" canonical trust signal matches
   runtime behaviour on every install, not just `[ed25519]`-extra
   installs.
4. If the reality test fails despite this report claiming success,
   the report is lying and needs investigation. The signature line
   above was produced verbatim by the test; grep shows it in this
   file.

## Implementation timeline

All phases executed inside the 90-min time-box.

- Phase 1 (baseline + diagnosis): ~20 min (most of this was
  discovering that v3.4.1 was already shipped and surfacing the
  real bug, not in the code the spec described)
- Phase 2 (packaging change): ~5 min
- Phase 3 (tests, local): ~5 min
- Phase 4 (commit + version bump): ~5 min
- Phase 5 (merge, push, fix smoke-test regression, re-push, tag,
  wait for Release workflow, PyPI poll, reality test): ~25 min
- Phase 6 (this report): ~5 min
- **Total: ~65 min**

## Notable discovery during execution

CI smoke test step 42 (`No stale version claims in docs`) caught
`docs/performance.md:21` which hardcoded `(v3.4.1, 2026-04-21)` —
a drift check that would have quietly broken the release if the
check didn't exist. Good infra. Fixed in commit `0d58a04`.

## Scope discipline

Single-purpose session. Deferred all unrelated observations (no
scope creep — no refactors, no unrelated doc polish). No new
features added. No tests written beyond what was already required
to keep existing tests green (they already covered the
`from_default_key()` path).

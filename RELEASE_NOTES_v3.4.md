# Sentinel v3.4.0 — Evidence Release

*Released 2026-04-20.*

v3.4.0 turns V8's canonical trust signals into shipped code. Every
claim on the unified homepage is now backed by a runtime primitive
with tests and a CLI — not a roadmap item.

## What is in this release

Four cryptographic features, one verb-aligned API, one homepage:

1. **Ed25519 signatures as default** — every attestation is signed by
   default, no `[pqc]` extra required.
2. **Hash-chain across attestations** — per-namespace chain back to
   a deterministic genesis; tampering breaks self-verify.
3. **PAdES PDF signing** — evidence-pack PDFs are cryptographically
   signed; Adobe Reader / Foxit verify them out of the box.
4. **RFC-3161 timestamping** — surfaced as a first-class trust
   signal alongside Ed25519. No code change; the existing
   `RFC3161Timestamper` already shipped in v3.1.
5. **`sentinel.trace / attest / audit / comply`** — the canonical
   v3.4 verb modules, narrow and well-documented.
6. **Unified V8 homepage** — one landing page, V8 marketing design
   merged with operational substance. `/platform.html` redirects
   to `/`.

## Upgrade in one command

```bash
pip install --upgrade 'sentinel-kernel[pdf]'
```

The `[pdf]` extra bundles `cryptography` (Ed25519 + X.509) and
`pyhanko` (PAdES) alongside `reportlab`. The bare install continues
to work — every v3.4 feature silently unavailable until the extras
are present.

Initialise the default signing key (optional — happens
automatically on first use):

```bash
sentinel key init
```

## Migration from v3.3.x

v3.4 is backward-compatible. Existing code keeps working.

### Signing defaults changed

`Sentinel()` now loads or creates an Ed25519 signer by default. To
preserve the pre-v3.4 "no signer" behaviour, pass `signer=None`
explicitly:

```python
from sentinel import Sentinel
sentinel = Sentinel()                 # v3.4: Ed25519-signed traces
sentinel = Sentinel(signer=None)      # pre-v3.4 behaviour
```

Or disable globally via env:

```bash
export SENTINEL_DEFAULT_SIGNER=off
```

The key file lives at `~/.sentinel/ed25519.key` (mode `0600`).
Override with `SENTINEL_KEY_PATH=/secure/keystore/agent.key`.

### API aliases

The long-form names are preserved. The shorter verb-module names
are the new canonical surface.

| Before                              | v3.4 canonical                  |
|-------------------------------------|---------------------------------|
| `generate_attestation(sentinel)`    | `attest.generate(sentinel)`     |
| `verify_attestation(envelope)`      | `attest.verify(envelope)`       |
| `sentinel.storage.query(...)`       | `audit.query(sentinel, ...)`    |
| `render_evidence_pdf(...)`          | `comply.export(sentinel, path)` |
| `sentinel.verify_integrity(id)`     | `audit.verify_trace(s, id)`     |

### Evidence packs are now PAdES-signable

`comply.export()` still produces an unsigned PDF by default. To
produce a PAdES-signed pack:

```bash
sentinel comply export -o pack.pdf   # unchanged
sentinel comply sign pack.pdf        # writes pack.signed.pdf
sentinel comply verify pack.signed.pdf
```

Embedding PAdES signing into `comply.export()` is tracked for v3.5.

### Attestation chaining is opt-in

Chain fields appear in the envelope only when you pass a
`chain_namespace`:

```python
from sentinel.chain import ChainNamespace, verify_chain
from sentinel.core.attestation import generate_attestation

ns = ChainNamespace("credit_agent", "EU-DE", "bafin-bait-8")

first  = generate_attestation(sentinel, chain_namespace=ns)
second = generate_attestation(
    sentinel,
    chain_namespace=ns,
    previous_hash=first["attestation_hash"],
)

result = verify_chain([first, second])
assert result.verified
```

Existing callers that do not pass `chain_namespace=` produce
identical envelopes to v3.3.

### Positioning updates

Public-facing copy now uses:

- *Evidence infrastructure for the regulated AI era* (formerly
  *Agility infrastructure*).
- *Trace. Attest. Audit. Comply.* as the operative lifecycle
  (formerly *Record. Enforce. Prove.*).

The CLAUDE.md visual-design chapter has been rewritten to V8
canonical (cream surfaces, Inter Tight, deep green accent, Lucide
icons). Future sessions producing visual surfaces default to V8.

## Sovereignty posture — unchanged

The three invariants are preserved:

1. **No US CLOUD Act exposure in the critical path.** `pyca/
   cryptography` and `pyhanko` are community-maintained (BSD/
   Apache / MIT), not US-incorporated entities, and make zero
   network calls at signing or verification time.
2. **Air-gapped operation still works.** Ed25519 key generation,
   signing, verification, PAdES signing, and chain walking are
   all fully local. No AIA resolution, no CRL download, no phone-
   home.
3. **Apache 2.0, permanently.** No relicensing. No commercial
   fork. No enterprise-only features in the kernel.

## Compatibility matrix

| Environment                      | v3.3 behaviour | v3.4 default behaviour |
|----------------------------------|----------------|------------------------|
| `pip install sentinel-kernel`    | No signing     | No signing (extra absent) |
| `pip install 'sentinel-kernel[pdf]'` | No signing | Ed25519 signing + PAdES |
| `pip install 'sentinel-kernel[pqc]'` | ML-DSA-65 signing | ML-DSA-65 (unchanged) |
| `SENTINEL_DEFAULT_SIGNER=off`    | (no effect)    | No signing (opt-out) |
| `Sentinel(signer=None)`          | No signing     | No signing (explicit) |

## Verification

```bash
pip install --upgrade 'sentinel-kernel[pdf]'

python - <<'PY'
from sentinel import Sentinel, trace, attest, audit, comply
print("imports OK")
s = Sentinel()
print("default signer:", getattr(s._signer, "algorithm", None))
PY

sentinel key public
sentinel chain verify examples/fixtures/sample_chain.json 2>/dev/null || true
```

If the first two print `imports OK` and `Ed25519`, your install is
complete.

## Links

- Full changelog: [CHANGELOG.md](CHANGELOG.md)
- Evidence module reference: [docs/sentinel-evidence.md](docs/sentinel-evidence.md)
- API stability contract: [docs/api-stability.md](docs/api-stability.md)
- Security posture: [docs/security-posture.md](docs/security-posture.md)

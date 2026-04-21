# Sentinel Evidence

*The third module of the four-module architecture. For the
product framing, see [docs/vision.md](vision.md). For the
provability conditions Evidence packs certify against, see
[docs/provability.md](provability.md).*

---

## What Evidence does

Sentinel Evidence turns the append-only `DecisionTrace` stream
that the **Trace** module captures, and the ALLOW / DENY /
EXCEPTION verdicts that the **Policy** module emits, into
artefacts an auditor accepts.

Three classes of artefact:

1. **Signed PDF evidence packs** — `sentinel evidence-pack
   --output audit.pdf`. Cover page, executive summary, framework
   coverage (EU AI Act / DORA / NIS2), trace samples, SHA-256
   hash manifest with pack-level digest, portable attestation
   appendix, dependency sovereignty scan. Reproducible from the
   same window of traces. Offline-verifiable.
2. **Portable attestations** — `sentinel attestation generate
   --output attestation.json`. Self-contained JSON with a
   SHA-256 digest over canonical content. Verifiable offline
   with `sentinel attestation verify`. No external service, no
   phone-home.
3. **Provability / compliance reports** — `sentinel report
   --output report.html`. Self-contained HTML, no CDN, safe to
   email. EU AI Act article-by-article status, dependency
   posture, recommended actions, manifesto check result.

Evidence is the module regulated buyers pay for. The base
generator is Apache 2.0; the enterprise features (see below)
are the commercial tier.

## Evidence route — how a runtime fact becomes defensible evidence

```
Runtime                 Queryable             Framework            Evidence
 trace         →         store       →         checker      →        pack
────────              ────────              ────────              ────────
DecisionTrace       sentinel.query()      EUAIActChecker       sentinel evidence-
written per         filters by window     DoraChecker          pack --output
decision. Schema-   project, agent,       NIS2Checker          audit.pdf. Signed,
versioned.          policy_result.        → per-article        reproducible.
Hash by default.                          status.
```

Each stage is idempotent and side-effect-free on the underlying
trace store. Evidence packs do not mutate traces; they
snapshot a window.

## Signatures — unsigned by default, ML-DSA-65 optional for long-retention archival

Sentinel ships one signing class today, activated at the
operator's discretion. The default is unsigned traces protected
by SHA-256 content hashing.

### Default — unsigned traces

The zero-config `Sentinel()` emits unsigned traces. Each trace
carries independent SHA-256 digests over inputs and outputs
(`inputs_hash`, `output_hash`) — these prove per-trace content
integrity, verifiable offline by hash recomputation. This is
appropriate for development and for deployments where trust in
the storage operator is already established.

Note the precise security property: SHA-256 content hashing
proves *integrity* against modification, but does not
*authenticate the producer*. An actor with write access to the
trace store can edit content and recompute hashes. Producer
authenticity and non-repudiation require the opt-in signing
path below.

### Opt-in — `QuantumSafeSigner` with ML-DSA-65 (FIPS 204)

```python
from sentinel import Sentinel
from sentinel.crypto import QuantumSafeSigner

signer = QuantumSafeSigner(
    key_path="/etc/sentinel/keys/signing.key",
    public_key_path="/etc/sentinel/keys/signing.pub",
)
sentinel = Sentinel(signer=signer)
```

`QuantumSafeSigner` loads a long-lived keypair the operator
generated offline via `sentinel keygen`. The default algorithm
is **ML-DSA-65** (FIPS 204, NIST post-quantum standard, BSI
TR-02102-1 recommended). `ML-DSA-44` and `ML-DSA-87` are also
supported via the `algorithm` constructor argument. Requires the
`sentinel-kernel[pqc]` extra (liboqs backend). Keys stay
operator-side; all operations run in-process; no external
service, no network call.

When a signer is configured, every trace acquires a
`signature` field (e.g. `"ML-DSA-65:<base64>"`) and a
`signature_algorithm` field. Signing failure is non-fatal —
storage always succeeds; a crypto error is captured as a trace
tag, not raised.

ML-DSA-65 is the correct choice when:

- Retention is **ten years or longer** (BaFin retention
  obligation on financial-sector AI decisions).
- The deployment targets BSI IT-Grundschutz certification, where
  TR-02102-1 algorithm conformance is expected.
- Quantum-era adversary models are part of the operator's
  threat matrix.

Sentinel does not lead with ML-DSA-65 as a headline feature —
it is available for the audience that asks for it specifically.

### Bring-your-own signer

The signer protocol is minimal: a `sign(data: bytes) -> str`
method (returning `"{algorithm}:{base64(sig)}"`), a
`verify(data: bytes, signature: str) -> bool` method, and an
`algorithm` attribute. Operators who need ECDSA, Ed25519, RSA,
or HSM-backed signing can implement this protocol and pass the
instance to `Sentinel(signer=...)`. See
[docs/security-posture.md](security-posture.md) for an HSM
adapter sketch — Sentinel does not ship an HSM abstraction
today.

## RFC-3161 timestamping via EU Timestamping Authorities

Signed artefacts can optionally include an RFC-3161 timestamp
from an EU-sovereign Timestamping Authority (TSA). Sentinel's
`RFC3161Timestamper` accepts only EU TSAs — DFN-CERT, D-Trust —
at construction time. US-based TSAs are rejected.

Air-gapped fallback: when no TSA is reachable, a local
timestamp is embedded and the artefact records that the
external timestamp was unavailable.

## Long-term retention — ten-plus-year archival

Archival deployments — BaFin retention obligations on financial
decisions, EU AI Act Art. 17 quality-management traceability —
combine three capabilities:

- **Append-only storage** with documented retention windows.
- **ML-DSA-65 signing** to survive cryptographic-era changes.
- **RFC-3161 timestamping** for temporal non-repudiation.
- **`sentinel purge --before <cutoff>`** for retention-window
  enforcement (dry-run by default).

See [docs/bsi-profile.md](bsi-profile.md) for the BSI
IT-Grundschutz mapping of retention controls, and
[docs/vsnfd-deployment.md](vsnfd-deployment.md) for the VS-NfD
classified-deployment profile.

## Evidence pack format — what an auditor receives

A `sentinel evidence-pack --output audit.pdf` produces a single
self-contained PDF with these sections, in order:

1. **Cover page.** Project, sovereign scope, data residency,
   storage backend, window, generation timestamp, scope
   reminder.
2. **Executive summary.** Traces in window, ALLOW / DENY /
   EXCEPTION_REQUIRED counts, human overrides, unique agents,
   unique policies.
3. **EU AI Act coverage** — Art. 9 / 12 / 13 / 14 / 17 article-
   by-article, same output as `sentinel compliance check`.
4. **DORA coverage** — optional, `--financial-sector`.
5. **NIS2 coverage** — optional, `--critical-infrastructure`.
6. **Trace samples** — first and last up to ten traces in the
   window, with hashed payloads where `store_inputs=False`.
7. **Hash manifest** — SHA-256 per-trace hashes plus a single
   pack-level digest over the whole list, so the document is
   tamper-evident against the NDJSON export of the same window.
8. **Portable attestation appendix** — `generate_attestation`
   output, self-contained, offline-verifiable.
9. **Dependency sovereignty scan** — total packages, jurisdiction
   breakdown, any critical-path violations.

All data is pulled from the same public APIs the CI check
uses. No network calls, no external services. Air-gap-capable.

## Enterprise tier — commercial features

The base generator is Apache 2.0. The commercial Evidence tier
addresses requirements that regulated enterprise buyers
actually have:

- **HSM integration** for key material — AWS CloudHSM, Azure
  Key Vault, Thales PKCS#11, Utimaco, Futurex. Sentinel does
  not ship an HSM abstraction today; the operator-side adapter
  pattern is sketched in
  [docs/security-posture.md](security-posture.md). A first-class
  `HSMSigner` class is a commercial-tier roadmap item, not yet
  shipped.
- **Multi-party signing** for critical decisions, with quorum
  policies configured per evidence pack.
- **Legal-hold management** — retention-window overrides for
  traces under legal hold, queryable as a first-class
  property on the trace.
- **Automated BaFin-reporting templates** — regulator-specific
  output formats (MaRisk reports, BaFin AI inventory).
- **RFC-3161 enterprise TSA contracts** — pre-negotiated EU
  TSA access with the SLAs regulated buyers need.
- **Retention-policy enforcement** — automated purge against
  operator-defined retention windows, with a dry-run
  verification workflow.

Contact sentinel@swentures.com or open a pilot enquiry on
GitHub for scope and pricing discussions.

## Verification — how an auditor independently checks the pack

See [docs/audit-verification-guide.md](audit-verification-guide.md)
for the full auditor workflow: hash verification, signature
verification, pack-manifest recomputation, raw-payload
reconstruction via out-of-band source-of-truth.

## Scope reminder

Sentinel Evidence produces evidence. It does not produce
compliance. Organisations produce compliance. An evidence pack
certifies the technical controls Sentinel is responsible for;
it does not discharge organisational obligations — risk
management plan (Art. 9), data governance documentation
(Art. 10), Annex IV technical documentation (Art. 11), accuracy
and robustness controls (Art. 15), conformity assessment, or
post-market monitoring — that sit above the kernel layer. See
[docs/eu-ai-act.md](eu-ai-act.md) for the full scope split.

## What's next — v3.5 Architecture Release

v3.5 (design phase, targeted next months) aligns Sentinel
Evidence with the **OpenTelemetry GenAI conventions** and
strengthens long-term retention:

- **OpenTelemetry GenAI integration** — parent-child trace
  context propagation; Sentinel attestations emitted as span
  events with `gen_ai.*` semantic attributes so Langfuse /
  Phoenix / Datadog / Grafana Tempo treat Sentinel evidence as
  first-class telemetry.
- **JSON-LD + PROV-O output format** — attestations written as
  W3C PROV-O JSON-LD, keeping ten-year archives machine-
  interpretable without a Sentinel-specific parser.
- **Fine-grained retention policies** — per-decision raw-vs-hash
  choice declared by the manifesto, informed by GDPR Art. 6/9
  legal basis and sector-specific retention law.
- **Write-once storage backends** — S3 Object Lock (compliance
  mode), Azure Blob Immutable Storage, POSIX append-only
  filesystem. WORM adherence for regulators that require
  operational tamper-evidence in addition to cryptographic.

See [docs/roadmap.md](roadmap.md) for the full phase plan. No
breaking changes to the v3.4 public API.

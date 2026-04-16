# For auditors

You received a `sentinel-kernel`-generated evidence pack. Your job is
to verify it independently, understand what it proves, and flag what
it does not.

## What you should have

1. A PDF — typically named `audit.pdf` or `evidence-pack-<period>.pdf`.
2. Optionally, an NDJSON export of the underlying traces.
3. Optionally, a public key (for cryptographic verification of the
   signature, if the deployment uses one).

## See a sample before anything else

- 📄 [Sample evidence pack (PDF)](../samples/audit-evidence-pack-sample.pdf)

The structure of a real pack matches this sample: cover page, executive
summary, per-article coverage table, trace samples, hash manifest with
a pack-level digest, sovereign attestation appendix, dependency
sovereignty scan.

## What the pack proves — and what it does not

**Proves:**

- The decisions were traced automatically, append-only (Art. 12).
- Agent identity, model identity, policy, and evaluator are recorded
  on every trace (Art. 13).
- A kill-switch mechanism exists and is exercised in CI (Art. 14).
- A schema-versioned, portable record format is in use (Art. 17).
- SHA-256 input/output hashes allow re-verification against the
  original payloads *if your client kept them*.

**Does not prove:**

- That the policy logic itself is correct. Sentinel records what the
  evaluator returned; it does not audit the evaluator.
- That the hashes are signed, unless the deployment registered a
  persistent signer. Ephemeral-key signatures cannot be verified
  across process restarts — ask the operator for their signer setup.
- That organisational Art. 9/10/11/15 obligations are met. Those live
  outside the trace layer.

## Independent verification path

```bash
# 1. Get the source
pip install sentinel-kernel

# 2. If traces were exported as NDJSON:
sentinel import --input traces.ndjson --db /tmp/audit-check.db
sentinel verify --all --db /tmp/audit-check.db

# 3. Expect: "verified: <N>, failed: 0".
```

`sentinel verify` recomputes every stored hash from the stored inputs
(if they were kept) and outputs (if they were kept). A mismatch means
the trace was mutated after creation.

## If the deployment used a persistent signer

Ask the operator for:

1. The public key (`signing.pub`).
2. The algorithm (default: `ML-DSA-65`, FIPS 204, BSI TR-02102-1).

```bash
sentinel verify --all --public-key signing.pub
```

Failure modes and their meaning are enumerated in
[audit-verification-guide.md](../audit-verification-guide.md) (if
present in your checkout; under construction).

## Common operator gotchas (what to ask for)

- "Is `store_inputs` / `store_outputs` enabled?" If False (the
  v3.2.0+ default), inputs and outputs are *not* in the trace —
  only their hashes are. That's by design for GDPR Art. 25. It also
  means you need to receive the raw payloads out-of-band if you
  intend to recompute the hashes.
- "Which signer is configured?" Ephemeral (default, per-process) or
  persistent (operator-generated keypair)? Ephemeral is useful only
  within a single process lifetime.
- "What is the data-residency assertion?" Every trace carries
  `data_residency` and `sovereign_scope`. The operator should be able
  to reproduce the same assertion from their deployment config.

## Commercial route

If your client needs BSI pre-engagement or structured audit-prep help,
that is scoped individually: see
[docs/commercial.md](../commercial.md).

# GDPR Art. 22 — explainable automated decisions

*How to use Sentinel when your deployment has to answer
"why was I declined?" to the data subject.*

## The tension

Sentinel defaults to **hash-only storage** (v3.2.0+) to minimise the
GDPR Art. 25 "data protection by design" liability. That default is
correct for the majority of regulated deployments. But GDPR Art. 22(3)
gives data subjects the right to "obtain human intervention, to express
his or her point of view, and to contest the decision" — which often
requires the operator to reconstruct *what was decided on*.

Hashes prove that a decision happened; they do not tell you *why*.

## The pattern

Keep the default for most of your deployment. Opt raw-output storage
in **only for the decision paths that need Art. 22 explanations**:

```python
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage

# General-purpose kernel — hash-only
general = Sentinel(
    storage=SQLiteStorage("/var/lib/sentinel/general.db"),
    project="platform",
)

# Art.-22-scoped kernel — raw outputs kept, raw inputs still hashed
art22 = Sentinel(
    storage=SQLiteStorage("/var/lib/sentinel/art22.db"),
    project="underwriting",
    store_inputs=False,   # inputs can be recovered from source-of-truth
    store_outputs=True,   # decision + reasoning kept for explanation
)
```

## Why this split works

| Need | Where it's satisfied |
|---|---|
| Art. 12 proof-of-logging | hash in either kernel |
| Art. 25 data-minimisation | hash-only in the general kernel |
| Art. 22 explanation on demand | raw output in the art22 kernel |
| Art. 15 accuracy record | raw output in the art22 kernel (model score, confidence, triggering feature set) |

The `store_outputs=True` kernel writes **only the model output** —
not the raw customer data, which typically lives in your CRM or
application database as the source-of-truth. The customer's right to
access (Art. 15) points to that system; the right to explanation
(Art. 22) points to Sentinel's output record.

## Writing the explanation

Inside your decorator, shape the output to carry the Art. 22 payload:

```python
@art22.trace(policy="policies/underwriting.py")
def underwrite(application: dict) -> dict:
    score, reasons = run_model(application)
    decision = "approve" if score > 0.65 else "decline"

    return {
        "decision": decision,
        "model_score": score,
        "top_reasons": reasons[:3],        # the Art. 22 explanation
        "model_version": "underwrit-v4.2",
        "policy_version": "UW-2026-Q2",
    }
```

The trace now carries the exact payload an Art. 22 response would
quote. Combined with the input hash (which proves which application
was processed), the record is complete.

## Data subject request workflow

A typical "why was I declined?" response:

```python
import json

traces = art22.query(project="underwriting", limit=1000)
relevant = [
    t for t in traces
    if t.inputs_hash == sha256_of_their_application
]
# relevant[0].output carries: decision, model_score, top_reasons,
# model_version, policy_version — everything Art. 22(3) requires.
```

Keep the **hash-matching lookup** out-of-band: the operator already
holds the original application (source-of-truth), hashes it with
Sentinel's canonical hash function, and pulls the matching trace.

```python
from sentinel.core.trace import DecisionTrace
target_hash = DecisionTrace._hash({"application": application_data})
```

## What this does NOT buy you

- It does not exempt you from Art. 22(2) conditions (explicit consent,
  contract necessity, or member-state law) — those remain
  organisational obligations.
- It does not replace the human-review step required by Art. 22(3) —
  Sentinel's kill switch and `HumanOverride` record are the evidence
  that a human reviewed, not the review itself.
- It does not make Sentinel a CRM or a model-registry — the raw input
  is still not stored. Only the output is.

## Retention

Art. 22 explanations are typically retained as long as the underlying
decision is contestable under your jurisdiction's civil-procedure
limitations. `sentinel fix retention --days 2555` (seven years) is a
common choice for financial underwriting; your DPO picks the number.

## Pilot / walkthrough

This is a non-obvious pattern worth walking through with someone who
has deployed it:
[Open a pilot enquiry on GitHub](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md).

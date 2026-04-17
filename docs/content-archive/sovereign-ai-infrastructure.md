# Why AI Decision Infrastructure Must Be Sovereign

## The invisible problem

Ask any engineering team running an LLM-backed agent in production
what they log. You will get an answer about token counts, latency
histograms, prompt strings, and maybe a structured output schema.
You will almost never get an answer about the *decision* — what the
model was asked to approve, which policy gated that approval, which
rule triggered a denial, who overrode it, or where that record
lives.

The trace that modern LLM observability stacks produce is a
performance trace, not a decision trace. It answers "how fast was
the model" and "what did it output". It does not answer the
question a regulator will ask in 2026: "prove to me, from your
audit log, that this specific action was authorised, by whom, and
under which policy". Most teams today cannot answer it at all. The
ones who can answer it are doing so with a scaffold of Google
Sheets, GitHub issues, and screenshotted Slack threads.

## 2 August 2026

On 2 August 2026, enforcement begins for high-risk AI systems under
Annex III of the EU AI Act. The core logging obligation is Article
12: a high-risk AI system must automatically log events over its
entire operational lifetime, in a way that enables traceability
of its functioning. Automatic. Over the operational lifetime.
Enables traceability. Three words, three architectural constraints.

Automatic rules out "the operator enables logging when they want
to". Over the operational lifetime rules out "we keep 30 days of
rolling data". Enables traceability rules out "we have token
counts and prompt strings, that's a trace". Article 13 adds
transparency obligations to deployers — the user of the system has
a right to understand how decisions are reached. Article 14 adds
human oversight, including the ability to halt the system. Article
17 requires the whole thing to be captured in a quality management
system.

Penalties for non-compliance are up to €15M or 3% of global annual
turnover, whichever is higher. For an Annex III high-risk system,
this is not optional. There is no grace period for a "we'll get to
it" stance.

## The CLOUD Act trap

Here is where an important asymmetry bites. The US Stored
Communications Act, as amended by the CLOUD Act (18 U.S.C. § 2713),
obligates US-incorporated entities to produce data in their
possession, custody, or control — regardless of where that data is
physically stored. The statute is unambiguous: a European
subsidiary running a European data centre, operated by a
US-incorporated company, is in possession, custody, and control of
the parent. A valid US legal process compels production. No
bilateral agreement, data processing addendum, or Schrems II
remediation changes this.

Draw the decision tree once and the architecture follows: is the
company providing my logging infrastructure US-incorporated? If
yes, the CLOUD Act applies to the audit record of every AI
decision my system makes. There is no configuration option that
turns this off. An EU-based data centre operated by a US-parent
company is the *worst* position to be in: it gives regulators the
illusion of data residency while giving US authorities an
unimpeded subpoena path.

This is not a theoretical concern. Defence, critical
infrastructure, financial services, and healthcare regulators in
the EU have explicitly flagged CLOUD Act exposure as a procurement
disqualifier. The EU AI Act does not name the CLOUD Act, but it
does require that logging be sufficient to prove compliance to an
EU regulator. A record that is simultaneously accessible to a US
prosecutor fails that test.

## What Article 12 actually requires

Strip away the legal hedging and Article 12 is a technical spec.

1. **Automatic.** No human step to initiate logging. The log event
   must happen at the same code boundary as the action being
   logged. In a wrapped decision function this means the trace must be
   emitted by the wrapper, not by the policy engine, not by the
   operator's dashboard.

2. **Tamper-resistant.** The log must be append-only at the
   storage layer. A schema field that can be updated after the
   fact is not a trace, it is a draft. Cryptographic hashing of
   the inputs and outputs makes a trace independently verifiable
   without requiring trust in the storage operator.

3. **Over the operational lifetime.** The retention horizon is
   longer than an observability tool's rolling window. The
   Commission's guidance is "as long as the system is in
   operation", which in practice means the full service life plus
   a multi-year tail for regulatory queries.

4. **Sufficient to reconstruct what happened.** Who initiated the
   action, what were the inputs, what policy ran, what was the
   result, who overrode it if anyone, what did the model output,
   when.

None of this is exotic. All of it is achievable with a small,
well-defined interceptor in the path between the agent and the
model. But the interceptor must be inside the operator's
jurisdictional boundary — not in an external service.

## The three tests

Three tests separate sovereign infrastructure from
sovereignty theatre.

**Jurisdiction.** No US-incorporated entity in the critical path
of a trace. The interceptor, the policy evaluator, the
serialisation layer, and the storage backend must all be operable
by entities not subject to the CLOUD Act. Open-source licensing is
necessary but not sufficient — Apache 2.0 does not change
jurisdiction.

**Air-gap.** The system must work fully offline. Not "offline with
telemetry disabled" — offline in the strict sense, with network
connections blocked at the socket level. Air-gap is the acid test
of whether the critical path has a hidden dependency. If the
system degrades when DNS fails, something in the critical path is
not local.

**Certification.** In Germany, BSI IT-Grundschutz is the
instrument. It is not mandatory for every AI deployment, but it is
the only path I know of to a government-backed assertion that a
sovereignty claim has been independently verified. For VS-NfD
(restricted classification) deployments, BSI assessment is a
prerequisite, not a nice-to-have.

Open source is necessary because you have to be able to inspect
and fork the code. Open source is not sufficient because inspection
doesn't change the license of a runtime dependency or the
nationality of a cloud provider.

## Manifesto as code

The gap between "our sovereignty policy" and "what's actually
running" is where failures happen. The fix is to express the
policy as code and run it in CI.

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    Required,
    ZeroExposure,
    AcknowledgedGap,
)

class ProductionPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    airgap = Required()
    cloud_act = ZeroExposure()

    # Honesty beats theatre. If you have a gap, name it and
    # commit to a migration plan.
    ci_cd = AcknowledgedGap(
        provider="GitHub (Microsoft)",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No production-ready EU-sovereign CI alternative today",
    )

report = ProductionPolicy().check(sentinel=my_sentinel)
```

The interesting part is `AcknowledgedGap`. Real systems have gaps.
A policy that pretends otherwise is a lie a regulator will catch.
A policy that names the gap, cites why no alternative exists, and
commits to a migration deadline is something a regulator can
actually work with. It is also something an engineering team can
defend in a procurement conversation.

The report the check produces distinguishes three tiers: hard
requirements that are met, hard requirements that are violated,
and acknowledged gaps with migration plans. CI fails on the
second. Honest reporting on the third is a feature, not a bug.

## Where we are

Sentinel v2.x is the stack I've been describing. It is 500+ tests,
100% coverage, and a zero-dependency core. The trace interceptor,
policy evaluator, and storage backends are all in-process. Air-gap
validation is a dedicated test suite that runs with the socket
layer monkey-patched to raise on any network call.

v2.1 adds `BudgetTracker` for client-side spend tracking, output
verification for tamper detection, and portable offline-verifiable
attestations. v2.2 adds quantum-safe signing — ML-DSA-65 (FIPS
204, BSI TR-02102-1 recommended) with keys held operator-side and
never sent anywhere. v2.3 adds a LangFuse sovereignty panel for
teams already running LangFuse. v2.4 adds a Rust implementation
of the RFC-001 manifesto spec, so the portability claim is not
just aspiration.

BSI pre-engagement material is in the repo. Linux Foundation
Europe stewardship is a planned conversation, not a claim. The
things that are not yet done are marked as not done.

## What to do now

```bash
# macOS (recommended)
brew install pipx && pipx install sentinel-kernel
sentinel demo

# Linux / Docker / CI
pip install sentinel-kernel
sentinel demo
```

That runs 50 decisions, engages the kill switch for five more,
runs the sovereignty scanner, runs the EU AI Act compliance check,
and generates a self-contained HTML report. No network, no API
key, no cloud account. The demo exists because the fastest way to
explain an interceptor is to run one.

The enforcement date for Annex III is 2 August 2026. The legal
penalty schedule has already been published. The procurement
conversations happening in Q4 2026 will be about systems that are
being built now, in April 2026. Decision trace infrastructure is
not the most glamorous piece of an AI platform, but it is the one
that converts a legal requirement into a technical fact. It is
also the one where the architectural choice — US-incorporated
provider versus sovereign stack — is binary, not a slider.

Pick sovereign. Write it down. Run the check in CI. Ship it.

## What comes after logging

Decision traces are the foundation, not the destination. Art. 12
compliance is the entry ticket — the question a regulated buyer asks
once the interceptor is in place is different, and harder: *which model
is even legal for this data class, and how do we prove the choice was
correct?* A trace that says "we sent this VS-NfD document to an API in
Oregon" is a well-logged mistake, not a sovereign decision.

The real question, one layer up, is model independence. The leading
proprietary platforms — we will not name them again — answer that
question by locking the buyer in: one ontology, one deployment
strategist, one jurisdiction, one vendor for the next decade. European
buyers who go that route are trading one structural dependency for
another, at enterprise-only commercial tiers. When LLMs guide their
own integration — and that is already happening at the agent layer —
the deployment-strategist moat evaporates. What survives is the
trusted kernel underneath: policy, audit trail, model router,
sovereignty proof.

That is where Sentinel is going in v4.0 with the `SovereignRouter`. The
same manifesto that already declares which dependencies and which
jurisdictions are acceptable will also declare which models are
permitted for each data class — and the kernel will select the model
automatically, record the choice and the reason in the sovereign trace,
and fall back if the preferred model is unavailable. The interface is
one call: `sentinel.route(task, context)`. The guarantee is that the
choice of model is a configuration of your manifesto, not a rewrite of
your code. That closes the loop. Sovereign trace (what), sovereign
governance (whether), sovereign routing (which model). One thin kernel.
Apache 2.0. Permanently. RFC-002 is open for comment.

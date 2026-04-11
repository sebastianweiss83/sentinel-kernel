# Sentinel — Quantum Systems Evaluation Package

Demonstrating Sentinel as the **L5 decision record layer** for
autonomous systems inside an EU-sovereign defence stack.

---

## The problem Sentinel solves

Autonomous systems make decisions. Under the EU AI Act and German
federal law, those decisions need a tamper-resistant record that:

- is written before the action is taken,
- identifies the model, the policy, and the outcome,
- remains under EU jurisdiction regardless of where the agent runs,
- supports human override (Art. 14) without restart,
- can be reproduced and audited years after the fact.

Today this evidence often lives in proprietary US platforms subject
to the CLOUD Act, or in ad-hoc logs that cannot be presented in a
legal proceeding. Sentinel is neither.

---

## What L5 means

In the autonomous-system stack we use the convention:

| Layer | Concern                       | Example          |
|-------|-------------------------------|------------------|
| L1    | Sensors                       | LiDAR, radar     |
| L2    | Perception                    | Object detection |
| L3    | Planning                      | Path planning    |
| L4    | Control                       | Motor commands   |
| **L5**| **Decision record**           | **Sentinel**     |

L5 sits **beside** L1–L4, not on top. Every decision produced by
any layer can be wrapped in a Sentinel trace without affecting the
execution path. The autonomous system behaves exactly as it did
before; the evidence record starts flowing.

---

## Running the demo

```bash
cd sentinel-kernel
python demo/qs/autonomous_decision_demo.py
```

This runs an offline demonstration of a VTOL mission planning agent
making go / no-go decisions. No API keys. No external network. The
mocked LLM is swapped for a deterministic decision function so the
demo is fully reproducible.

### What you'll see

```
================================================================
  QS AUTONOMOUS DECISION DEMO — VTOL mission planner
================================================================
  Mission 1: transport, 80km, wind 12 kt   -> GO
  Mission 2: transport, 450km, wind 12 kt  -> NO_GO (out_of_range)
  Mission 3: recon, 120km, wind 35 kt      -> NO_GO (wind_over_limit)
  [human operator engages kill switch: 'ground all missions']
  Mission 4: transport, 80km, wind 10 kt   -> BLOCKED (kill switch)
  [kill switch disengaged]
  Mission 5: transport, 80km, wind 10 kt   -> GO
  ...
  Sovereignty score: 100%
  Traces: 5 (1 DENY by policy, 1 blocked by kill switch, 3 GO)
```

---

## Why this matters for QS

- **EU AI Act Art. 14** mandates human override. The Sentinel kill
  switch is the reference implementation — it blocks execution,
  writes a linked DENY trace, and requires zero restart. A demo of
  this in action is the fastest route to Art. 14 sign-off.
- **BSI IT-Grundschutz** is the federal standard that will gate
  German defence procurement. Sentinel's v1.0 milestone is a
  formal IT-Grundschutz assessment.
- **CLOUD Act.** Every layer of the QS autonomous stack that runs
  on US-owned software is a jurisdictional risk. Sentinel's
  critical path has no US-owned components — by design, not by
  configuration.

---

## Integration effort

Realistic estimate for a first integration with an existing QS
autonomous decision path:

| Step                                    | Effort  |
|-----------------------------------------|---------|
| Wrap one decision function with `@sentinel.trace` | 1 hour |
| Configure sovereignty metadata          | 30 min  |
| Add a policy (`SimpleRuleEvaluator`)     | 2 hours |
| Hook kill switch to an operator control  | 4 hours |
| Wire OTel export to QS observability    | 1 day   |
| End-to-end validation + CI integration  | 2 days  |

Total for a first working integration: **one week** of a single
senior engineer's time. No dependency on an external platform.

---

## Next step

A joint 2-hour technical deep-dive where we wire Sentinel into one
of your existing autonomous decision flows live, on your codebase.
Contact sebastian@swentures.com.

# EU Sovereignty Rules — Non-Negotiable

## The three laws

### 1. No US CLOUD Act exposure in the critical path
Any US-incorporated entity in the trace emission path creates CLOUD Act
exposure regardless of server location. An EU data centre run by a US
company does not solve this. US services may appear only in optional
integrations, clearly marked as non-sovereign.

### 2. Air-gapped must always work
Local file storage is the reference deployment for classified environments.
Test offline before marking any feature complete.

### 3. Apache 2.0, forever
No licence change. No CLA enabling relicensing. No closed-source features.

## Before adding any dependency (document in PR every time)
1. Who is the parent company?
2. US-incorporated?
3. Makes network calls at runtime?
4. Works pinned and offline?
If 2 and 3 are both yes: not in the critical path.

## What EU-sovereign means
Does NOT mean: cannot use code written by Americans.
DOES mean: no US company has runtime access to decision traces.
DOES mean: EU law governs all data at rest and in transit.
DOES mean: a regulator can independently verify the data residency claim.

# examples/policies/data_classification.rego
#
# Document sensitivity classification policy.
#
# Determines whether an agent is permitted to process or release a
# document based on its classification level, the agent's clearance,
# and the destination jurisdiction. Every DENY records the triggering
# rule so an auditor can reconstruct the decision.
#
# Classification lattice (public → secret):
#   UNCLASSIFIED  — no restriction
#   INTERNAL      — organisation-only
#   RESTRICTED    — named workgroup
#   CONFIDENTIAL  — role-based, justification required
#   SECRET        — cleared principals only, air-gapped egress
#
# Rego version: Rego v1 (OPA 0.60+)

package sentinel

default allow := false
default deny_reason := null

# Principals without a recorded clearance can only touch UNCLASSIFIED.
allow if {
    input.input.document.classification == "UNCLASSIFIED"
}

# INTERNAL — requires the principal to belong to the owning organisation.
allow if {
    input.input.document.classification == "INTERNAL"
    input.input.principal.organisation == input.input.document.owning_organisation
}

# RESTRICTED — requires principal to be a named member of the workgroup.
allow if {
    input.input.document.classification == "RESTRICTED"
    input.input.principal.organisation == input.input.document.owning_organisation
    input.input.document.workgroup_id in input.input.principal.workgroups
}

# CONFIDENTIAL — requires role-based clearance and a recorded justification.
allow if {
    input.input.document.classification == "CONFIDENTIAL"
    input.input.principal.clearance_level >= 3
    input.input.justification
    count(input.input.justification) >= 20
}

# SECRET — cleared principals, and the request must be air-gapped.
allow if {
    input.input.document.classification == "SECRET"
    input.input.principal.clearance_level >= 4
    input.input.destination.network == "air-gapped"
    input.input.principal.organisation == input.input.document.owning_organisation
}

# ---------------------------------------------------------------------------
# Deny reasons — ordered most specific → least specific
# ---------------------------------------------------------------------------

deny_reason := "cross_organisation_leak" if {
    not allow
    input.input.document.classification != "UNCLASSIFIED"
    input.input.principal.organisation != input.input.document.owning_organisation
}

deny_reason := "insufficient_clearance" if {
    not allow
    input.input.document.classification == "CONFIDENTIAL"
    input.input.principal.clearance_level < 3
}

deny_reason := "missing_justification" if {
    not allow
    input.input.document.classification == "CONFIDENTIAL"
    input.input.principal.clearance_level >= 3
    not input.input.justification
}

deny_reason := "justification_too_short" if {
    not allow
    input.input.document.classification == "CONFIDENTIAL"
    input.input.justification
    count(input.input.justification) < 20
}

deny_reason := "secret_requires_airgap" if {
    not allow
    input.input.document.classification == "SECRET"
    input.input.destination.network != "air-gapped"
}

deny_reason := "secret_insufficient_clearance" if {
    not allow
    input.input.document.classification == "SECRET"
    input.input.principal.clearance_level < 4
}

deny_reason := "unknown_classification" if {
    not allow
    not input.input.document.classification in ["UNCLASSIFIED", "INTERNAL", "RESTRICTED", "CONFIDENTIAL", "SECRET"]
}

deny_reason := "no_matching_rule" if {
    not allow
    not deny_reason
}

# ---------------------------------------------------------------------------
# Test cases — run with: opa test examples/policies/
# ---------------------------------------------------------------------------

test_unclassified_always_allowed if {
    allow with input as {"input": {
        "document": {"classification": "UNCLASSIFIED"},
        "principal": {"clearance_level": 0},
    }}
}

test_secret_cross_network_denied if {
    deny_reason == "secret_requires_airgap" with input as {"input": {
        "document": {"classification": "SECRET", "owning_organisation": "org-A"},
        "principal": {"clearance_level": 4, "organisation": "org-A"},
        "destination": {"network": "internet"},
    }}
}

test_confidential_without_justification_denied if {
    deny_reason == "missing_justification" with input as {"input": {
        "document": {"classification": "CONFIDENTIAL", "owning_organisation": "org-A"},
        "principal": {"clearance_level": 3, "organisation": "org-A"},
    }}
}

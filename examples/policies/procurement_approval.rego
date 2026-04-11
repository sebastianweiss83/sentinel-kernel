# examples/policies/procurement_approval.rego
#
# Procurement approval policy with amount threshold and requester level.
#
# Used by: examples/04_policy_rego.py
#
# Rego version: Rego v1 (OPA 0.60+)
# Run against: LocalRegoEvaluator(opa_binary="opa")
#
# Decision shape expected by Sentinel:
#   data.sentinel = {
#     "allow":       bool,
#     "deny_reason": string | null,
#   }

package sentinel

default allow := false
default deny_reason := null

# Allow small requests from any requester level >= 1
allow if {
    input.input.request.amount <= 10000
    input.input.request.requester_level >= 1
}

# Allow medium requests from requester level >= 2
allow if {
    input.input.request.amount <= 100000
    input.input.request.requester_level >= 2
}

# Allow large requests only from requester level >= 3
allow if {
    input.input.request.amount <= 1000000
    input.input.request.requester_level >= 3
}

# Explain the denial for audit
deny_reason := "amount_exceeds_requester_authority" if {
    not allow
    input.input.request.amount > 10000
}

deny_reason := "amount_exceeds_cap" if {
    not allow
    input.input.request.amount > 1000000
}

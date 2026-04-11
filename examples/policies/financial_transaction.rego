# examples/policies/financial_transaction.rego
#
# Financial transaction approval policy.
#
# Evaluates amount limits, velocity checks, sanctions hits, and
# customer risk tier. Designed for automated real-time decisioning
# with a full audit trail. Every DENY records the triggering rule.
#
# Rego version: Rego v1 (OPA 0.60+)

package sentinel

default allow := false
default deny_reason := null

# Baseline: allow up to customer's per-transaction limit
allow if {
    input.input.tx.amount <= input.input.customer.per_tx_limit
    input.input.customer.sanctions_score < 10
    input.input.customer.velocity_last_hour < input.input.customer.velocity_limit
    input.input.customer.risk_tier != "HIGH"
}

# HIGH-risk customers must have tx amount under a much stricter cap
allow if {
    input.input.customer.risk_tier == "HIGH"
    input.input.tx.amount <= 500
    input.input.customer.sanctions_score < 5
    input.input.customer.velocity_last_hour < 5
}

# Sanctions hit — hard deny regardless
deny_reason := "sanctions_hit" if {
    input.input.customer.sanctions_score >= 10
}

# Velocity breach
deny_reason := "velocity_limit_exceeded" if {
    not allow
    input.input.customer.velocity_last_hour >= input.input.customer.velocity_limit
}

# Per-transaction limit breach
deny_reason := "per_tx_limit_exceeded" if {
    not allow
    input.input.tx.amount > input.input.customer.per_tx_limit
}

# High-risk customer cap
deny_reason := "high_risk_cap_exceeded" if {
    not allow
    input.input.customer.risk_tier == "HIGH"
    input.input.tx.amount > 500
}

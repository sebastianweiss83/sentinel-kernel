# sentinel/examples/policies/discount_approval.rego
# 
# Discount approval policy for enterprise sales.
# This is an example — copy and adapt to your use case.
#
# OPA docs: https://www.openpolicyagent.org/docs/latest/policy-language/

package sentinel.discount

import future.keywords.if
import future.keywords.in

# Default: deny unless explicitly allowed
default allow = false
default deny_reason = null

# Standard discounts: always allowed
allow if {
    input.request.discount_pct <= 10
}

# Enterprise tier: up to 25% allowed
allow if {
    input.request.discount_pct <= 25
    input.customer.tier == "enterprise"
}

# Reason for denial — surfaces in the decision trace
deny_reason = "discount_exceeds_standard_cap" if {
    not allow
    input.request.discount_pct > 10
    input.customer.tier != "enterprise"
}

deny_reason = "discount_exceeds_enterprise_cap" if {
    not allow
    input.request.discount_pct > 25
    input.customer.tier == "enterprise"
}

# Flags that require human escalation
exception_required if {
    input.request.discount_pct > 25
}

exception_required if {
    input.customer.has_open_legal_dispute == true
}

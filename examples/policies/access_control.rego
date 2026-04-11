# examples/policies/access_control.rego
#
# Role-based access control policy.
#
# Maps principals (users, services) and their roles to permitted
# actions on resources. Every DENY records the triggering rule so
# an auditor can reconstruct exactly which access attempt was blocked.
#
# Rego version: Rego v1 (OPA 0.60+)

package sentinel

default allow := false
default deny_reason := null

# Admin can do anything
allow if {
    input.input.principal.role == "admin"
}

# Clinician can read patient records in their unit
allow if {
    input.input.principal.role == "clinician"
    input.input.action == "read"
    input.input.resource.type == "patient_record"
    input.input.resource.unit_id == input.input.principal.unit_id
}

# Billing can read anonymised aggregates, never identifiable records
allow if {
    input.input.principal.role == "billing"
    input.input.action == "read"
    input.input.resource.type == "aggregate"
}

# Any authenticated user can read their own profile
allow if {
    input.input.action == "read"
    input.input.resource.type == "user_profile"
    input.input.resource.user_id == input.input.principal.user_id
}

# Deny reason: unauthenticated
deny_reason := "no_authenticated_principal" if {
    not allow
    not input.input.principal
}

# Deny reason: unit mismatch
deny_reason := "unit_mismatch" if {
    not allow
    input.input.principal.role == "clinician"
    input.input.resource.unit_id != input.input.principal.unit_id
}

# Default deny reason
deny_reason := "no_matching_rule" if {
    not allow
    input.input.principal
    not deny_reason
}

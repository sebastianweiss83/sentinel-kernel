# examples/policies/medical_escalation.rego
#
# Treatment recommendation escalation policy.
#
# Routes AI-generated treatment recommendations based on patient
# risk score and adverse-event history. Low risk goes to the
# treating clinician for acknowledgement; medium risk requires a
# second opinion; high risk always halts and is escalated.
#
# This is a reference template, not clinical advice.
#
# Rego version: Rego v1 (OPA 0.60+)

package sentinel

default allow := false
default deny_reason := null

# Low risk — single clinician sign-off
allow if {
    input.input.patient.risk_score < 3
    input.input.patient.previous_adverse_events == 0
}

# Medium risk — allow but require second opinion flag already set
allow if {
    input.input.patient.risk_score >= 3
    input.input.patient.risk_score < 7
    input.input.second_opinion_obtained == true
}

# High risk — always escalate, never allow automatic action
deny_reason := "risk_score_requires_escalation" if {
    not allow
    input.input.patient.risk_score >= 7
}

# Medium risk without second opinion
deny_reason := "second_opinion_required" if {
    not allow
    input.input.patient.risk_score >= 3
    input.input.patient.risk_score < 7
    input.input.second_opinion_obtained != true
}

# Prior adverse events always trigger escalation regardless of score
deny_reason := "adverse_event_history_requires_review" if {
    not allow
    input.input.patient.previous_adverse_events > 0
}

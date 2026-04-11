# examples/policies/mission_safety.rego
#
# Autonomous system mission-safety policy.
#
# Evaluates go / no-go for autonomous missions based on range,
# weather, and payload. All DENY decisions record a named rule so
# an accident investigator can reconstruct the reasoning years later.
#
# Generic template — adapt the thresholds to your specific system.
#
# Rego version: Rego v1 (OPA 0.60+)

package sentinel

default allow := false
default deny_reason := null

# Defaults for a reference VTOL-class asset
MAX_RANGE_KM := 300
MAX_WIND_KT := 25
MAX_VISIBILITY_DROP := 5  # km

allow if {
    input.input.mission.range_km <= MAX_RANGE_KM
    input.input.mission.wind_kt <= MAX_WIND_KT
    input.input.mission.visibility_km >= MAX_VISIBILITY_DROP
    input.input.mission.payload_hazard_class == "none"
}

deny_reason := "out_of_range" if {
    not allow
    input.input.mission.range_km > MAX_RANGE_KM
}

deny_reason := "wind_over_limit" if {
    not allow
    input.input.mission.wind_kt > MAX_WIND_KT
}

deny_reason := "visibility_below_minima" if {
    not allow
    input.input.mission.visibility_km < MAX_VISIBILITY_DROP
}

deny_reason := "hazardous_payload_requires_manual_approval" if {
    not allow
    input.input.mission.payload_hazard_class != "none"
}

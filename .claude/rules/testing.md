# Testing

## Five mandatory tests per feature
1. Happy path
2. Offline — local storage, zero network
3. Policy DENY — blocks execution, DENY recorded with rule name
4. Override — second linked trace entry, original untouched
5. EU AI Act fields — all mandatory fields present and correct

## Sovereignty tests — CI blockers (every PR)
- test_offline_mode_emits_complete_trace
- test_all_eu_ai_act_fields_present
- test_trace_is_immutable_after_write
- test_deny_records_triggering_rule
- test_override_creates_linked_entry

## Coverage
Core trace emission: 95%+ / Storage interface: 90%+ / Integrations: 80%+

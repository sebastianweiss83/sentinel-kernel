# /project:add-integration
Scaffold a new AI framework or model provider integration.

## Usage: /project:add-integration [name]

## Before writing any code
Read docs/integration-guide.md. Answer and document in your PR:
1. Does this framework send data to a US-owned service?
2. Does it work fully offline?
3. Does it introduce a US dependency in the critical path? If yes: stop.

## What to build
- sentinel/integrations/[name] — implements standard middleware interface, works offline
- tests/integrations/test_[name] — trace emitted, DENY recorded, override linked, no-network test
- examples/[name]_quickstart — under 30 lines, local storage only
- Update README integrations table and docs/integration-guide.md

## Non-negotiables
No mandatory network call. No breaking change to storage interface.
Sovereignty must be documentable.

# ADR-005 - boot_id for device sessions

Date: 2026-10-03
Status: Accepted

## Decision

Dedup key becomes `(device_id, boot_id)` with `boot_id: str = ""` by default. One window per session, same sliding rules inside each.

## Why

Sequence counters reset on reboot, so `(device_id, sequence)` alone misreads fresh post reboot packets as TOO_OLD. The empty default keeps old payloads and old tests working: no boot info just means the legacy session.

## Alternatives considered

- Epoch numbers: same idea, strings are simpler to generate and read in JSON.
- Fold reboot into TOO_OLD handling: wrong, it would drop valid data.
- Wiping device state on low seq: guessing, a legit delayed packet would nuke real window state.

## Consequence

State grows per session, so very chatty rebooters could pile up sessions. Cleanup or expiry of dead sessions is a future problem, noted not solved.

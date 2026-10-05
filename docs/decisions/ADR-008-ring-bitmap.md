# ADR-008 - Ring bitmap to remove shifting

Date: 2026-10-05
Status: Accepted

## Decision

Add `RingBitmapSlidingWindowDeduplicator` with fixed bytearray slots and a rotating `start_index`. TOO_OLD decided from seq vs window start before any slot access. Older implementations untouched.

## Why

Pure bitmap shifts the whole int on every advance. A ring removes that cost while keeping exact semantics. Bytearray picked for readable per slot updates, not for compactness. Slot reuse correctness (TOO_OLD before slot consult) is the load bearing rule.

## Alternatives considered

- Keep shifting bitmap: leaves suspected slide cost unaddressed.
- Bit packed ring in an int: cleverer, harder to read while learning circular indexing.

## Consequence

Three implementations share one API and result type. Three way benchmark comes next.

# ADR-003 - Sequence number window, not arrival window

Date: 2026-10-02
Status: Accepted

## Decision

The window is a range over sequence numbers `[max_seq - W + 1, max_seq]`, not the last W arrivals.

## Why

Arrival order windows slide on every packet including retries, so entries get evicted by arrival recency and legit retries can read as NEW twice. A sequence number window has stable meaning: anything below it is TOO_OLD, anything inside but unseen is a valid late arrival, anything seen is a DUPLICATE.

## Alternatives considered

- Last N received: simple, wrong semantics under reordering (see journey 004).
- Unbounded set: correct, grows forever.

## Consequence

Eviction rule is fixed: on a new high `seq`, drop everything at or below `seq - W`. Memory stays O(W) per device.

# ADR-002 - Sequence numbers as dedup identity

Date: 2026-10-02
Status: Accepted

## Decision

Dedup key is `(device_id, sequence)`. Values and timestamps are never part of identity.

## Why

Retried packets reuse the same sequence number, so identity by sequence catches exactly the at least once delivery dupes without ever judging sensor values. Two identical readings in a row might be a stable sensor, not a dupe, and dropping those would destroy real data. Value based filtering is a separate future feature with its own thresholds.

## Alternatives considered

- Hash of full payload: breaks on retries that refresh timestamps.
- Value comparison: conflates stable readings with duplicates.

## Consequence

Gaps in sequences are fine (lost packets), reordering is fine (jitter). Anything about values waits for the anomaly stage.

# ADR-001 - Exact dedup before anything probabilistic

Date: 2026-10-02
Status: Accepted

## Decision

Keep the exact `set[int]` sliding window as the reference implementation. No Bloom filter, no bitmap yet.

## Why

I need a ground truth to compare every future optimization against. If a Bloom prefilter or bitmap port ever disagrees with this implementation, the optimization is wrong, not the reference. Correctness first, memory second.

## Alternatives considered

- Bitmap: still exact and way smaller, but harder to read while Im still learning the semantics.
- Ring buffer: great for windows, more fiddly to get right.
- Bloom filter: smallest, but lies sometimes (false positives drop valid telemetry) and windowing is awkward.

## Consequence

Higher memory per device for now. That gets revisited with real comparison numbers in a later entry.

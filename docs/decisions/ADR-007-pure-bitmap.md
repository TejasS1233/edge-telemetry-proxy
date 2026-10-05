# ADR-007 - Pure bitmap as second implementation

Date: 2026-10-05
Status: Accepted

## Decision

Add `BitmapSlidingWindowDeduplicator` as a separate class using a Python int as the window bitmap. Baseline untouched. Physically shifting the int on advance is accepted for now.

## Why

Tests the 005 prediction (exact, tiny memory) with the simplest possible bitmap before learning ring indexing. Shifting cost is knowingly deferred to the ring step so each optimization is measured separately.

## Alternatives considered

- Ring immediately: skips a learning step and merges two measurements into one.
- External bit array lib: unnecessary, ints already do arbitrary bit ops.

## Consequence

Same API as baseline, shared result types, differential fuzz clean. Benchmark decides if the memory win is real.

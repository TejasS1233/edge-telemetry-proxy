# ADR-006 - Baseline memory via tracemalloc, workload materialized first

Date: 2026-10-04
Status: Accepted

## Decision

Measure the exact set baseline with stdlib `tracemalloc` around pipeline processing only. Materialize the workload with `list(generate_telemetry(...))` before starting the trace and timer. Label the output as traced allocs, not RSS. No `psutil`.

## Why

The generator is lazy, so tracing the old streaming loop would have counted workload objects as dedup memory. Materializing first keeps attribution clean: pre existing allocations are invisible to tracemalloc, so the traced number is the dedup state plus transient processing overhead. stdlib means zero new dependencies for a prototype.

## Alternatives considered

- `psutil` RSS: one number mixing workload, interpreter and dedup state. Could not answer how much is the dedup state itself.
- Trace the streaming loop as is: misleading, generator builds its objects inside the traced region.
- Restructure the generator for measurement: out of scope, explicitly deferred. One line in the benchmark instead.

## Consequence

The materialized list lives in real untraced RAM, so actual process RSS exceeds traced MB on big runs (notably 100K devices). Both numbers are reported honestly for what they are. Future bitmap and Bloom comparisons reuse this exact harness.

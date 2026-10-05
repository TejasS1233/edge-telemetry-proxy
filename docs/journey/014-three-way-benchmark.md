# 014 - Three-way benchmark, ring included

Date: 2026-10-05

## What I had

Two implementations measured against each other and a ring with no numbers. The benchmark only knew set and bitmap, so the ring could not be compared on equal footing.

## The problem

Same fairness problem as before: identical workload, separate trace sessions, loud failure on mismatch, now with three contenders. The harness change had to stay as small as the two-way version.

## What I learned

The ring landed where theory said it should: memory right next to the bitmap (bytearray costs real bytes per slot, so it climbs with window while the int bitmap barely moves), throughput best in 3 of 4 within-run pairs. And a useful reminder about measurement itself: the whole machine ran slower that session, so cross session eps numbers are noise and only within-run ordering means anything. Full table in `docs/experiments/004-implementation-comparison.md`.

## What changed

Benchmark gained the `ring` option and compare mode now runs all three on one shared workload with a three-way match check. No changes to any implementation.

## Next

The exact structures are done and measured. The remaining question from 005 is the probabilistic one: Bloom prefilter in front, with the exact set as ground truth for false positives.

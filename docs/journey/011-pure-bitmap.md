# 011 - Pure bitmap dedup

Date: 2026-10-05

## What I had

A correct exact set baseline with measured memory: ~2.35 KB traced per device at window 32, linear in device count. The 005 comparison table had predicted a bitmap would be way smaller while staying exact. Time to test that claim instead of just believing the table.

## The problem

The set stores full Python ints per seen sequence, around 28 bytes each plus set overhead. But a window only needs one yes/no answer per sequence number. That is a bit, not an object. The question was whether a bitmap keeps identical semantics (NEW / DUPLICATE / TOO_OLD, gaps, jumps, boot isolation) without the set.

## What I learned

A plain Python int works as the bitmap, no dependency needed. Bit 0 is the oldest seq in `[max - W + 1, max]`, bit W-1 is max itself. Advancing by delta shifts right by delta, which drops exactly the evicted seqs. Jumps past the whole window just zero the int. The differential fuzz against the baseline (20 trials x 500 random events, mixed windows, devices, boots, gaps) gave 0 mismatches, which is what made me trust it. Full numbers in `docs/experiments/004-implementation-comparison.md`.

## What changed

New `src/bitmap_dedup.py` with `BitmapSlidingWindowDeduplicator`, same API as the baseline, baseline file untouched. 15 focused tests. Benchmark gained `--implementation set|bitmap|compare` with a shared workload and a loud mismatch failure.

## Next

Compare the two on identical workloads and see what the memory and throughput numbers actually say.

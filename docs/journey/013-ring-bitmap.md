# 013 - Ring bitmap, no more shifting

Date: 2026-10-05

## What I had

A pure bitmap with great memory but a suspected slide cost: every window advance shifts the whole int. The fix from the 005 table was always going to be a ring: fixed slots, a rotating start index, never move stored bits. Full credit to my friend Rishit Sharma here, he had already taught me this circular indexing idea so I came in aware of it and just had to implement it right.

## The problem

The one trap that makes rings tricky: a physical slot represents different seqs over time. If u ever read a slot without checking the seq is still in the window, an evicted seq can false match against a new seq reusing its slot. The design rule that prevents it: TOO_OLD is decided purely from seq vs window start, before any slot is touched. Slots are only consulted for seqs known to be inside.

## What I learned

Advancing is just clearing the departing seqs slots and bumping `start_index` by delta mod W. Nothing stored ever moves. I verified the nasty case by hand: window 5, 100-104 in, 105 steals slot 0 from 100, then 100 reads TOO_OLD (never consults the reused slot) while 105 reads DUPLICATE off it. Differential fuzz against both older implementations (30 trials x 500 events, windows 1-32, gaps, jumps, multiple boots) gave 0 mismatches across all three.

## What changed

New `src/ring_bitmap_dedup.py` with `RingBitmapSlidingWindowDeduplicator`, bytearray slots, explicit `start_index` / `window_start` / `logical_offset` / `physical_index` naming. Both older implementations untouched. 18 focused tests including explicit slot reuse cases. Benchmark comparison comes next, deliberately not in this step.

## Next

Benchmark all three on the shared workload harness and see if the ring keeps the bitmap memory while fixing the suspected slide cost.

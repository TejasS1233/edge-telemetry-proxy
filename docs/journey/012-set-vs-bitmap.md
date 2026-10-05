# 012 - Set vs bitmap on identical workloads

Date: 2026-10-05

## What I had

Two verified implementations and a compare mode that replays one shared workload through both, each in its own tracemalloc session, failing loudly on any count mismatch. Ran windows 8, 32, 128, 1024 at 10K devices x 100 events.

## The problem

None in execution. The interest was all in the numbers, which are filed in full at `docs/experiments/004-implementation-comparison.md`. Short version: correctness matched on all four windows, bitmap state memory came out 5x to 40x smaller and nearly flat across windows (1.6 to 3.2 MB), while the set climbed with window size as before.

## What I learned

Two things. First, the memory win is real and structural: a few hundred bits per device plus object overhead versus full int objects per seen seq. Second, throughput refused to tell a clean story. Bitmap was faster in 3 of 4 within-run pairs but slower at window 32, and absolute numbers jumped between runs on identical workloads. So per the house rule: shifting cost may matter, but these runs do not isolate the cause. That unresolved question is exactly what motivates the next step.

## What changed

No code for correctness, only measurement. The comparison results are the evidence the ring bitmap needs to beat or explain.

## Next

Kill the shifting. A ring bitmap that rotates an index instead of moving bits should keep the memory win and remove the suspected slide cost.

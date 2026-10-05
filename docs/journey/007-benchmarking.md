# 007 - First benchmark numbers

Date: 2026-10-02

## What I had

A benchmark script that generates a configurable workload and runs it through the pipeline: device count, events per device, dupe rate, out of order rate, window size. No broker involved, pure pipeline speed plus dedup stats.

## The problem

My first generator version had a stupid bug that the benchmark caught immediately. I flattened all device streams and did one global shuffle to simulate shared ingress. That randomly permuted each device's own packet order, so per device arrivals looked like chaos. Result: 709k TOO_OLD out of 1.1M events and a fake 67% reduction rate. The numbers were nonsense and the benchmark is what exposed it.

## What I learned

Interleaving has to preserve per device order. The fix was an ordered merge: each device emits its own packets in order, and the generator randomly picks which device speaks next. That models a shared edge link without scrambling sequence order. After the fix the numbers look sane. Also learned that writing the benchmark before trusting any claim was the right call. Without it I would have shipped a broken simulator.

## What changed

Fixed the generator merge. Default workload (10k devices x 100 events, 10% dupes, 5% out of order, window 32) now gives:

- total 1,100,359, NEW 989,817, DUPLICATE 98,430, TOO_OLD 12,112
- forwarded 989,817, dropped 110,542, reduction 10.05%
- around 46k events per sec on my machine

Full table lives in `docs/experiments/001-baseline.md`.

## Next

Bigger question waiting: per device set memory at scale, and whether a bitmap port keeps up. That is a future entry with real comparison numbers, not opinions.

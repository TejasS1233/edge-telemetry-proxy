# 001 - Baseline runs

Workload unless noted: 10% dupes, 5% out of order, 2% late, seed 42. In process path (no broker).

## Default run (10K devices x 100 events, window 32)

- total received: 1,100,359
- NEW: 989,817
- DUPLICATE: 98,430
- TOO_OLD: 12,112
- forwarded: 989,817
- dropped: 110,542
- reduction: 10.05%
- time: ~24s, around 46k events per sec

## Small run (100 devices x 50 events)

- total: 5,495, NEW: 4,949, DUPLICATE: 481, TOO_OLD: 65
- forwarded: 4,949, dropped: 546, reduction 9.94%
- around 100k+ events per sec (less contention, tiny state)

## The broken run that taught me smth

First generator version did a flat global shuffle across devices. That scrambled per device order and gave 709k TOO_OLD out of 1.1M with a fake 67% reduction. Fixed with an ordered merge (each device emits in order, random pick of which device speaks next). Details in `../journey/007-benchmarking.md`.

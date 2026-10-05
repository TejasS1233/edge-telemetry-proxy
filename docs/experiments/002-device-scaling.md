# Device scaling (window 32, 100 events per device)

Same workload mix every run: 10% dupes, 5% out of order, 2% late, seed 42. Only device count changes. Memory is Python traced allocs during pipeline processing, not total RSS.

| Devices | Events    | Peak traced MB | Events/s | Reduction |
|---------|-----------|----------------|----------|-----------|
| 1K      | 109,954   | 2.34           | 46,797   | 9.96%     |
| 10K     | 1,100,359 | 23.33          | 34,230   | 10.05%    |
| 50K     | 5,500,584 | 117.71         | 23,057   | 10.02%    |
| 100K    | 11,001,582| 235.41         | 20,434   | 10.02%    |

## What stands out

Peak memory goes 2.34 -> 23.33 (9.97x) -> 117.71 (5.05x) -> 235.41 (2.00x). That is linear in device count, around 2.35 KB traced per device at window 32. Strong evidence the exact set state behaves as O(devices x window).

Reduction sits at ~10% in every run, so the workload mix is scale invariant and the dedup semantics hold steady.

Throughput decreased as the number of tracked devices increased (46k -> 20k events/s). This suggests that increasing state size and associated Python runtime overhead may affect processing performance, but the current experiment does not isolate the cause. Investigating that comes later.

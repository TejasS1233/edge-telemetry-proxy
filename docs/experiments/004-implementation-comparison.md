# Implementation comparison (10K devices x 100 events, shared workload per window)

Same workload mix every run: 10% dupes, 5% out of order, 2% late, seed 42. One materialized workload replayed through each implementation in separate tracemalloc sessions. Memory is Python traced allocs during processing, not total RSS. Correctness matched on every run (identical NEW / DUPLICATE / TOO_OLD / forwarded / dropped / reduction).

## Set vs bitmap

| Window | Set peak | Bitmap peak | Set eps | Bitmap eps |
|--------|----------|-------------|---------|------------|
| 8      | 8.68 MB  | 1.61 MB     | 25,818  | 46,715     |
| 32     | 23.33 MB | 1.92 MB     | 42,540  | 34,468     |
| 128    | 81.92 MB | 2.03 MB     | 20,934  | 28,633     |
| 1024   | 81.92 MB | 3.18 MB     | 24,879  | 26,936     |

Bitmap 5x to 40x smaller and nearly flat across windows, since a few hundred bits plus per session object overhead barely moves. Set climbs with window then plateaus at events per device.

## Set vs bitmap vs ring

| Window | Set peak | Bitmap peak | Ring peak | Set eps | Bitmap eps | Ring eps |
|--------|----------|-------------|-----------|---------|------------|----------|
| 8      | 8.68 MB  | 1.61 MB     | 2.31 MB   | 23,043  | 36,544     | 33,462   |
| 32     | 23.33 MB | 1.92 MB     | 2.54 MB   | 21,302  | 27,282     | 36,929   |
| 128    | 81.92 MB | 2.03 MB     | 3.45 MB   | 19,923  | 25,111     | 36,797   |
| 1024   | 81.92 MB | 3.18 MB     | 12.00 MB  | 19,841  | 22,965     | 35,076   |

Ring memory sits right next to the bitmap. Bytearray of W bytes per device plus object overhead, which is why it climbs to 12 MB at window 1024 while the int based bitmap stays at 3.18 MB.

Throughput, both tables: mixed and noisy. Ring fastest in 3 of 4 within-run pairs here, bitmap took one, and absolute numbers jump between sessions on identical workloads (set at window 32 did ~42k eps in the two-way session vs ~21k in the three-way one). Only within-run ordering carries weight, and even that flips, so no causal claims. The runs do not isolate the cause.

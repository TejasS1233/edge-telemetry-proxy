# Window scaling (10K devices, 100 events per device)

Same workload mix every run: 10% dupes, 5% out of order, 2% late, seed 42. Only window size changes. Memory is Python traced allocs during pipeline processing, not total RSS.

| Window | Events    | Peak traced MB | Events/s | TOO_OLD  | Reduction |
|--------|-----------|----------------|----------|----------|-----------|
| 8      | 1,100,312 | 8.68           | 87,495   | 18,588   | 10.51%    |
| 32     | 1,100,359 | 23.33          | 45,262   | 12,112   | 10.05%    |
| 128    | 1,099,908 | 81.92          | 67,506   | 0        | 9.08%     |
| 1024   | 1,099,908 | 81.92          | 20,795   | 0        | 9.08%     |

## What stands out

Memory grows with the window from 8 to 128, then flatlines: 128 and 1024 report identical 81.92 MB. That makes sense because each device only ever sends 100 events, so no window bigger than 100 ever fills up. Every device just ends up holding all 100 seqs. Memory here is really O(devices x min(window, events per device)).

TOO_OLD hits 0 at window 128 and stays there, same reason. Nothing ever gets evicted, so nothing can arrive too late.

Throughput does not move in one direction (87k -> 45k -> 67k -> 21k). Window 128 is faster than 32 here, which suggests eviction work and set rebuild churn play a role, but this experiment does not isolate the cause. Not drawing conclusions yet.

Open question for later: rerun the big windows with more events per device (say 2000) so the window actually fills, and see if memory keeps climbing with window size past 128.

# Experiments

Measured numbers for the edge telemetry dedup work, in the order they ran. Memory everywhere is Python traced allocs during pipeline processing, not total RSS.

| # | Experiment | What it showed |
|---|-----------|----------------|
| 001 | [Baseline runs](001-baseline.md) | Default and small workload numbers, plus the broken shuffle run |
| 002 | [Device scaling](002-device-scaling.md) | 1K to 100K devices, peak memory scales linearly |
| 003 | [Window scaling](003-window-scaling.md) | Windows 8 to 1024, memory plateaus past events per device |
| 004 | [Implementation comparison](004-implementation-comparison.md) | Set vs bitmap vs ring, all matched, ring near bitmap memory |

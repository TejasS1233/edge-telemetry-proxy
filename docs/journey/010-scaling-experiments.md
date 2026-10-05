# 010 - Scaling experiments confirm O(devices x window)

Date: 2026-10-04

## What I had

A benchmark that could finally measure dedup state memory (009), and a hypothesis from way back in 005: the exact set implementation should behave as O(devices x window). Time to check instead of assume. Two sweeps planned: device count at fixed window, then window size at fixed device count.

## The problem

None in execution, the runs just took a while (the 100K run is 11M events, about 9 minutes of processing). The interesting part was all in the numbers.

Device sweep at window 32: peak memory went 2.34 -> 23.33 -> 117.71 -> 235.41 MB across 1K to 100K devices. Dead linear, about 2.35 KB traced per device. Hypothesis confirmed for the device axis. Full table in `docs/experiments/002-device-scaling.md`.

Window sweep at 10K devices (8, 32, 128, 1024): memory climbs then flatlines, with 128 and 1024 reporting identical numbers. Full table in `docs/experiments/003-window-scaling.md`.

## What I learned

Memory grows with window until it does not. Windows 128 and 1024 report identical 81.92 MB because each device only sends 100 events, so no window above 100 ever fills. Every device just holds all 100 seqs. The real behavior is O(devices x min(window, events per device)), which is obvious in hindsight but I only believe it because the numbers say so. TOO_OLD hitting exactly 0 at 128+ backs it up: nothing evicted, nothing arriving late.

On throughput I am deliberately careful. It falls with device count (46k -> 20k) and jumps around in the window sweep (87k -> 45k -> 67k -> 21k). This suggests state size and associated runtime overhead may matter, but these experiments do not isolate the cause, so no conclusions. Investigating that is future work, not this entry.

## What changed

Results filed topic wise in `docs/experiments/002-device-scaling.md` and `docs/experiments/003-window-scaling.md`, with the experiments index at `docs/experiments/README.md`. Full raw outputs kept in the experiment notes.

## Next

Open question for later: rerun big windows with more events per device (say 2000) so the window actually fills past 128, and confirm memory keeps climbing. Then the bitmap comparison has a real baseline to beat.

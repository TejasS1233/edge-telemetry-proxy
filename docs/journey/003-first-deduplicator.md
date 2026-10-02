# 003 - Building the first deduplicator

Date: 2026-10-01

## What I had

Nothing but the reframed plan from 002. So I built the tiniest pipeline that could work:

```
Telemetry
  |
SlidingWindowDeduplicator
  |
NEW / DUPLICATE / TOO_OLD -> FORWARD or DROP
```

One dataclass for the event (device_id, sequence, timestamp, metric, value), one dedup class with a `check(telemetry)` method, one pipeline that maps NEW to FORWARD and everything else to DROP. Plus a fake telemetry generator so I could test without real devices.

## The problem

My first mental model of a duplicate was pretty naive but here it is:

```python
if sequence <= last_seen:
    drop()
```

Looks reasonable for like two seconds. Then packets arrive out of order and the whole thing falls apart. This exact sequence from the tests shows it:

```
100 -> NEW
101 -> NEW
103 -> NEW
102 -> NEW
103 -> DUPLICATE
```

When 102 arrives, `last_seen` is already 103. The naive check says `102 <= 103`, drop it. But 102 was never seen before. That is valid telemetry getting thrown away. So the naive rule confuses "smaller number" with "already received" and those are not the same thing at all.

## What I learned

Duplicate detection is a membership question (have I seen this exact seq before) not an ordering question (is this seq smaller than the max). Once I framed it that way the fix was obvious: keep the actual set of seen sequences per device instead of one lonely `last_seen` number.

## What changed

The dedup state became per device `max_seq` plus a `seen` set, and the result type became three states instead of two: NEW, DUPLICATE, and TOO_OLD for stuff that arrives after its window already slid past. TOO_OLD matters because it tells u the packet was valid once but ur too late, which is different from a retry.

## Next

The set works but "keep everything" is not a real design. I need to bound the memory with a proper window and figure out the eviction rules.

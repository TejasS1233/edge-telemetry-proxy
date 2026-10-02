# 004 - Sliding windows, and the mistake that taught me the most

Date: 2026-10-02

## What I had

After 003 I had per device `max_seq` plus a `seen` set, but no bound on growth. My first thought was "just keep the last N packets" which sounds fine until u ask what "last N" even means when packets arrive out of order.

## The problem

There are two totally different ideas hiding behind "window" and I was mixing them up:

1. last N received packets (whatever arrived most recently, in arrival order)
2. sequence number window `[max_seq - W + 1, max_seq]` (a range over sequence numbers)

Option 1 breaks badly. Say window is 5 and u receive 100, 101, 102, 103, 104, then a delayed 95 shows up followed by a retry of 100. With "last 5 received" the set holds whatever came last, so old entries get pushed out by arrival order and a legit retry of 100 might read as NEW again. The window slides on arrivals, not on sequence numbers, so it has no stable meaning.

## What I learned

The window has to live in sequence number space, not arrival space. The rule that fell out:

- `seq in seen` -> DUPLICATE
- `seq < max_seq - W + 1` -> TOO_OLD
- else -> NEW, and if `seq > max_seq`, slide the window and evict everything at or below `seq - W`

And the mistake from 003 deserves repeating because it is the most instructive one in the whole project so far:

```python
# wrong, drops valid reordered packets
if sequence <= last_seen:
    drop()
```

`102 <= 103` does not mean "seen before". Membership means seen before. One integer cannot answer a set question.

## What changed

`SlidingWindowDeduplicator` now stores exactly the window `[max_seq - W + 1, max_seq]` per device and evicts on every new high. Memory is O(W) per device, lookups are O(1). The spec example passes: after accepting 100 to 104 with W=5, an incoming 99 reads TOO_OLD, and a retry of 103 reads DUPLICATE.

## Next

Do the uncomfortable math: is a Python `set[int]` per device actually okay at 10k or 100k devices. That leads straight into bitmaps and Bloom filters.

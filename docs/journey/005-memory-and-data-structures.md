# 005 - Set vs bitmap vs Bloom, and why Bloom is not automatically better

Date: 2026-10-02

## What I had

A correct exact dedup (004) with one nagging question: if I have 100k devices each holding a Python `set[int]` of size 32, is that actually reasonable on an edge box.

## The problem

Back of envelope math says maybe not. A Python int is ~28 bytes, a set entry with overhead is way more than the 4 bytes the number actually needs. Times 32 entries times 100k devices, that is real money on a small gateway. So I started comparing options instead of just assuming Bloom filter = better:

| Approach    | Exact? | Memory   | Windowing/deletion | Complexity |
|-------------|--------|----------|--------------------|------------|
| Set         | Yes    | High     | Easy               | Low        |
| Bitmap      | Yes    | Very low | Good               | Medium     |
| Ring bitmap | Yes    | Very low | Excellent          | Higher     |
| Bloom       | No     | Very low | Tricky             | Medium     |

## What I learned

Bloom is not automatically better, and writing that down matters. It saves memory but it lies sometimes: false positives mean a NEW packet reads as DUPLICATE and valid telemetry gets dropped silently. For an edge proxy that is the worst kind of wrong. Plus deletion and sliding windows are awkward in a plain Bloom, u need counting variants or rotating filters, which adds the complexity back.

So the honest ordering is: exact set now (ground truth), then a bitmap or ring buffer port for memory (still exact), then optionally a Bloom prefilter in front, measured against the exact version so the false positive cost is visible instead of hidden.

## What changed

Nothing in code yet, and that is the point. The decision got recorded first: keep `set[int]` as the reference implementation until correctness and benchmarks are established. Bitmap and Bloom come later as measured optimizations, not rewrites based on vibes. See ADR-001.

## Next

Wire up real MQTT ingress so the pipeline eats actual broker traffic instead of in process generator output. That is a bigger learning step than another data structure right now.

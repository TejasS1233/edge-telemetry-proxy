# 009 - Measuring baseline memory with tracemalloc

Date: 2026-10-04

## What I had

A benchmark that measured throughput and dedup counts but had zero visibility into memory. Journey 005 had already asked the uncomfortable question (is a set per device okay at 100k devices) and the only honest answer is numbers. So the goal was simple: add memory measurement to the baseline before any bitmap or Bloom work begins.

## The problem

Two traps showed up before writing a single line. First, `generate_telemetry()` is lazy. Calling it builds nothing, the per device lists materialize on first `next()`, which happens inside the timed loop. So the old timer was quietly including generation time, and any memory trace around that loop would have counted every `Telemetry` object the generator builds as if it were dedup state. That would have been a nonsense measurement dressed up as a real one.

Second, what tool. `psutil` gives process RSS but that mixes everything (workload list, interpreter, dedup state) into one number. `tracemalloc` only tracks Python allocations made while tracing is active, which means pre existing objects are invisible to it. That property is exactly what I needed.

## What I learned

The fix was one line with outsized importance: materialize the workload with `list(generate_telemetry(...))` before starting the trace and the timer. Everything the generator builds then exists before tracing starts, so the traced number answers one clean question: how much does pipeline processing itself allocate. Which is basically the dedup state plus transient result objects.

Also learned to be precise about what the number is not. It is not RSS, it misses C level allocations, and the materialized workload list sits in real RAM outside the trace. For the 100K run that list is 11M objects, way bigger than the traced 235 MB. Both numbers are true, they just answer different questions.

## What changed

Benchmark now starts tracemalloc after workload creation, stops it in a `finally` so it always stops cleanly, and prints a labeled memory section that says traced allocs, not RSS. Timer now covers processing only. Return type fixed to `dict[str, int | float]`. No changes to dedup, generator, pipeline, or tests. See ADR-006.

## Next

Run the actual scaling experiments against this baseline: devices first, then window sizes.

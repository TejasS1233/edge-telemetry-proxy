from __future__ import annotations

import argparse
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import generate_telemetry
from src.bitmap_dedup import BitmapSlidingWindowDeduplicator
from src.dedup import DedupStatus, SlidingWindowDeduplicator
from src.pipeline import Decision, EdgePipeline
from src.ring_bitmap_dedup import RingBitmapSlidingWindowDeduplicator


def build_workload(
    num_devices: int = 10_000,
    events_per_device: int = 100,
    duplicate_pct: float = 0.10,
    out_of_order_pct: float = 0.05,
    late_pct: float = 0.02,
    window_size: int = 32,
    seed: int = 42,
) -> list:
    # materialized once, so every implementation replays the same events
    return list(
        generate_telemetry(
            num_devices=num_devices,
            events_per_device=events_per_device,
            duplicate_pct=duplicate_pct,
            out_of_order_pct=out_of_order_pct,
            late_pct=late_pct,
            window_size=window_size,
            seed=seed,
        )
    )


def run_pipeline(events: list, window_size: int = 32, implementation: str = "set") -> dict[str, int | float]:
    if implementation == "bitmap":
        pipeline = EdgePipeline(deduplicator=BitmapSlidingWindowDeduplicator(window_size=window_size))
    elif implementation == "ring":
        pipeline = EdgePipeline(deduplicator=RingBitmapSlidingWindowDeduplicator(window_size=window_size))
    elif implementation == "set":
        pipeline = EdgePipeline(deduplicator=SlidingWindowDeduplicator(window_size=window_size))
    else:
        raise ValueError(f"unknown implementation: {implementation}")
    counts = {"NEW": 0, "DUPLICATE": 0, "TOO_OLD": 0, "FORWARD": 0, "DROP": 0}
    total = 0

    tracemalloc.start()
    start = time.perf_counter()
    try:
        for event in events:
            result = pipeline.process(event)
            total += 1
            if result.dedup.status == DedupStatus.NEW:
                counts["NEW"] += 1
            elif result.dedup.status == DedupStatus.DUPLICATE:
                counts["DUPLICATE"] += 1
            else:
                counts["TOO_OLD"] += 1
            if result.decision == Decision.FORWARD:
                counts["FORWARD"] += 1
            else:
                counts["DROP"] += 1
    finally:
        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    eps = total / elapsed if elapsed > 0 else 0.0
    reduction = (counts["DROP"] / total * 100.0) if total else 0.0
    return {
        "total": total,
        "new": counts["NEW"],
        "duplicate": counts["DUPLICATE"],
        "too_old": counts["TOO_OLD"],
        "forwarded": counts["FORWARD"],
        "dropped": counts["DROP"],
        "reduction_pct": reduction,
        "seconds": elapsed,
        "events_per_second": eps,
        "mem_current_mb": current / (1024 * 1024),
        "mem_peak_mb": peak / (1024 * 1024),
    }


def run_benchmark(
    num_devices: int = 10_000,
    events_per_device: int = 100,
    duplicate_pct: float = 0.10,
    out_of_order_pct: float = 0.05,
    late_pct: float = 0.02,
    window_size: int = 32,
    seed: int = 42,
    implementation: str = "set",
) -> dict[str, int | float]:
    # build the full workload first, so gen time and its objects
    # stay out of the timer and the memory trace below
    events = build_workload(
        num_devices=num_devices,
        events_per_device=events_per_device,
        duplicate_pct=duplicate_pct,
        out_of_order_pct=out_of_order_pct,
        late_pct=late_pct,
        window_size=window_size,
        seed=seed,
    )
    return run_pipeline(events, window_size=window_size, implementation=implementation)


def check_match(baseline: dict, contender: dict, name: str) -> None:
    keys = ("total", "new", "duplicate", "too_old", "forwarded", "dropped", "reduction_pct")
    mismatched = [k for k in keys if baseline[k] != contender[k]]
    if mismatched:
        details = ", ".join(f"{k}: set={baseline[k]} {name}={contender[k]}" for k in mismatched)
        raise SystemExit(f"CORRECTNESS MISMATCH between set and {name}: {details}")


def print_metrics(title: str, metrics: dict) -> None:
    print(title)
    print(f"total events received : {metrics['total']:,}")
    print(f"NEW events            : {metrics['new']:,}")
    print(f"DUPLICATE events      : {metrics['duplicate']:,}")
    print(f"TOO_OLD events        : {metrics['too_old']:,}")
    print(f"events forwarded      : {metrics['forwarded']:,}")
    print(f"events dropped        : {metrics['dropped']:,}")
    print(f"reduction percentage  : {metrics['reduction_pct']:.2f}%")
    print(f"processing time       : {metrics['seconds']:.3f}s")
    print(f"events per second     : {metrics['events_per_second']:,.0f}")
    print("=== Memory (Python traced allocs during processing, not total RSS) ===")
    print(f"current traced memory : {metrics['mem_current_mb']:.2f} MB")
    print(f"peak traced memory    : {metrics['mem_peak_mb']:.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark edge telemetry deduplication.")
    parser.add_argument("--num-devices", type=int, default=10_000)
    parser.add_argument("--events-per-device", type=int, default=100)
    parser.add_argument("--duplicate-pct", type=float, default=0.10)
    parser.add_argument("--out-of-order-pct", type=float, default=0.05)
    parser.add_argument("--late-pct", type=float, default=0.02)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--implementation", choices=("set", "bitmap", "ring", "compare"), default="set")
    args = parser.parse_args()

    workload_kwargs = dict(
        num_devices=args.num_devices,
        events_per_device=args.events_per_device,
        duplicate_pct=args.duplicate_pct,
        out_of_order_pct=args.out_of_order_pct,
        late_pct=args.late_pct,
        window_size=args.window_size,
        seed=args.seed,
    )
    if args.implementation == "compare":
        # one shared workload, each impl traced in its own session
        events = build_workload(**workload_kwargs)
        set_metrics = run_pipeline(events, window_size=args.window_size, implementation="set")
        bitmap_metrics = run_pipeline(events, window_size=args.window_size, implementation="bitmap")
        ring_metrics = run_pipeline(events, window_size=args.window_size, implementation="ring")
        check_match(set_metrics, bitmap_metrics, "bitmap")
        check_match(set_metrics, ring_metrics, "ring")
        print_metrics("=== Exact set ===", set_metrics)
        print_metrics("=== Pure bitmap ===", bitmap_metrics)
        print_metrics("=== Ring bitmap ===", ring_metrics)
        print("correctness: MATCH (counts identical)")
        return

    metrics = run_benchmark(**workload_kwargs, implementation=args.implementation)
    print_metrics(f"=== Edge Telemetry Dedup Benchmark ({args.implementation}) ===", metrics)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import generate_telemetry
from src.dedup import DedupStatus
from src.pipeline import Decision, EdgePipeline


def run_benchmark(
    num_devices: int = 10_000,
    events_per_device: int = 100,
    duplicate_pct: float = 0.10,
    out_of_order_pct: float = 0.05,
    late_pct: float = 0.02,
    window_size: int = 32,
    seed: int = 42,
) -> dict[str, int | float]:
    pipeline = EdgePipeline(window_size=window_size)
    counts = {"NEW": 0, "DUPLICATE": 0, "TOO_OLD": 0, "FORWARD": 0, "DROP": 0}
    total = 0

    # build the full workload first, so gen time and its objects
    # stay out of the timer and the memory trace below
    events = list(
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark edge telemetry deduplication.")
    parser.add_argument("--num-devices", type=int, default=10_000)
    parser.add_argument("--events-per-device", type=int, default=100)
    parser.add_argument("--duplicate-pct", type=float, default=0.10)
    parser.add_argument("--out-of-order-pct", type=float, default=0.05)
    parser.add_argument("--late-pct", type=float, default=0.02)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    metrics = run_benchmark(
        num_devices=args.num_devices,
        events_per_device=args.events_per_device,
        duplicate_pct=args.duplicate_pct,
        out_of_order_pct=args.out_of_order_pct,
        late_pct=args.late_pct,
        window_size=args.window_size,
        seed=args.seed,
    )
    print("=== Edge Telemetry Dedup Benchmark ===")
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


if __name__ == "__main__":
    main()

from __future__ import annotations

import random
import time
from collections.abc import Iterator

try:
    from src.telemetry import Telemetry
except ImportError:
    from telemetry import Telemetry  # type: ignore[no-redef]


def _build_device_sequence(
    rng: random.Random,
    device_id: str,
    events_per_device: int,
    duplicate_pct: float,
    out_of_order_pct: float,
    late_pct: float,
    window_size: int,
    base_sequence: int,
    start_time: float,
    boot_id: str = "",
) -> list[Telemetry]:
    seqs = list(range(base_sequence, base_sequence + events_per_device))

    # sprinkle in some retries
    stream: list[int] = []
    for seq in seqs:
        stream.append(seq)
        if rng.random() < duplicate_pct:
            stream.append(seq)

    # shuffle things a little, stays inside window
    max_swap = max(1, min(8, window_size - 1))
    i = 0
    while i < len(stream) - 1:
        if rng.random() < out_of_order_pct:
            distance = rng.randint(1, max_swap)
            j = min(len(stream) - 1, i + distance)
            stream[i], stream[j] = stream[j], stream[i]
            i += distance + 1
        else:
            i += 1

    # push a few packets way back so they land too old
    n_late = int(len(stream) * late_pct)
    for _ in range(n_late):
        if len(stream) < window_size + 2:
            break
        src = rng.randrange(0, len(stream) - window_size - 1)
        slack = rng.randint(1, 5)
        dst = min(len(stream), src + window_size + slack)
        stream.insert(dst, stream.pop(src))

    events: list[Telemetry] = []
    for offset, seq in enumerate(stream):
        events.append(
            Telemetry(
                device_id=device_id,
                sequence=seq,
                timestamp=start_time + offset * 0.01,
                metric="temperature",
                value=20.0 + rng.gauss(0.0, 2.0),
                boot_id=boot_id,
            )
        )
    return events


def generate_telemetry(
    num_devices: int = 10,
    events_per_device: int = 100,
    duplicate_pct: float = 0.10,
    out_of_order_pct: float = 0.05,
    late_pct: float = 0.02,
    window_size: int = 32,
    seed: int | None = None,
    base_sequence: int = 1,
    interleave: bool = True,
    boot_id: str = "",
) -> Iterator[Telemetry]:
    rng = random.Random(seed)
    start_time = time.time()
    per_device: list[list[Telemetry]] = []
    for d in range(num_devices):
        device_id = f"device-{d:05d}"
        per_device.append(
            _build_device_sequence(
                rng, device_id, events_per_device, duplicate_pct,
                out_of_order_pct, late_pct, window_size, base_sequence, start_time,
                boot_id,
            )
        )
    if not interleave:
        for events in per_device:
            yield from events
        return
    # mix devices but keep each device's own order intact
    remaining = [len(events) for events in per_device]
    indices = [0] * num_devices
    active = [i for i, n in enumerate(remaining) if n > 0]
    while active:
        pick_pos = rng.randrange(len(active))
        d = active[pick_pos]
        yield per_device[d][indices[d]]
        indices[d] += 1
        if indices[d] >= remaining[d]:
            active[pick_pos] = active[-1]
            active.pop()

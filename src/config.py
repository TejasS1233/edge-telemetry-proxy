from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EdgeConfig:
    window_size: int = 32
    num_devices: int = 10_000
    events_per_device: int = 100
    duplicate_pct: float = 0.10
    out_of_order_pct: float = 0.05
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be >= 1")
        if self.num_devices < 1:
            raise ValueError("num_devices must be >= 1")
        if self.events_per_device < 1:
            raise ValueError("events_per_device must be >= 1")
        for name in ("duplicate_pct", "out_of_order_pct"):
            pct = getattr(self, name)
            if not 0.0 <= pct <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

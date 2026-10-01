from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Telemetry:
    device_id: str
    sequence: int
    timestamp: float
    metric: str
    value: float

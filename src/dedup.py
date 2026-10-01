from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .telemetry import Telemetry


class DedupStatus(str, Enum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    TOO_OLD = "TOO_OLD"


@dataclass(frozen=True, slots=True)
class DedupResult:
    status: DedupStatus
    device_id: str
    sequence: int


@dataclass
class _DeviceWindow:
    max_seq: int
    seen: set[int] = field(default_factory=set)


class SlidingWindowDeduplicator:
    def __init__(self, window_size: int = 32) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self._devices: dict[str, _DeviceWindow] = {}

    @property
    def devices_tracked(self) -> int:
        return len(self._devices)

    def check(self, telemetry: Telemetry) -> DedupResult:
        device_id = telemetry.device_id
        seq = telemetry.sequence
        state = self._devices.get(device_id)

        # brand new device, nothing to compare yet
        if state is None:
            self._devices[device_id] = _DeviceWindow(max_seq=seq, seen={seq})
            return DedupResult(DedupStatus.NEW, device_id, seq)

        # seen it already
        if seq in state.seen:
            return DedupResult(DedupStatus.DUPLICATE, device_id, seq)

        # fell behind the window, too late
        if seq < state.max_seq - self.window_size + 1:
            return DedupResult(DedupStatus.TOO_OLD, device_id, seq)

        if seq > state.max_seq:
            # new high, slide window forward
            state.max_seq = seq
            state.seen.add(seq)
            cutoff = seq - self.window_size
            state.seen = {s for s in state.seen if s > cutoff}
        else:
            # arrived out of order but still in window
            state.seen.add(seq)

        return DedupResult(DedupStatus.NEW, device_id, seq)

    def reset(self, device_id: str | None = None) -> None:
        if device_id is None:
            self._devices.clear()
        else:
            self._devices.pop(device_id, None)

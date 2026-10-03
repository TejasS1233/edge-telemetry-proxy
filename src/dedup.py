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
    boot_id: str = ""


@dataclass
class _DeviceWindow:
    max_seq: int
    seen: set[int] = field(default_factory=set)


class SlidingWindowDeduplicator:
    def __init__(self, window_size: int = 32) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self._devices: dict[tuple[str, str], _DeviceWindow] = {}

    @property
    def devices_tracked(self) -> int:
        return len(self._devices)

    def check(self, telemetry: Telemetry) -> DedupResult:
        device_id = telemetry.device_id
        seq = telemetry.sequence
        boot_id = telemetry.boot_id
        key = (device_id, boot_id)
        state = self._devices.get(key)

        # brand new device session, nothing to compare yet
        if state is None:
            self._devices[key] = _DeviceWindow(max_seq=seq, seen={seq})
            return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

        # seen it already
        if seq in state.seen:
            return DedupResult(DedupStatus.DUPLICATE, device_id, seq, boot_id)

        # fell behind the window, too late
        if seq < state.max_seq - self.window_size + 1:
            return DedupResult(DedupStatus.TOO_OLD, device_id, seq, boot_id)

        if seq > state.max_seq:
            # new high, slide window forward
            state.max_seq = seq
            state.seen.add(seq)
            cutoff = seq - self.window_size
            state.seen = {s for s in state.seen if s > cutoff}
        else:
            # arrived out of order but still in window
            state.seen.add(seq)

        return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

    def reset(self, device_id: str | None = None, boot_id: str | None = None) -> None:
        if device_id is None:
            self._devices.clear()
        elif boot_id is None:
            # clear every session of this device
            for key in [k for k in self._devices if k[0] == device_id]:
                del self._devices[key]
        else:
            self._devices.pop((device_id, boot_id), None)

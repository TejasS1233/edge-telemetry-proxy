from __future__ import annotations

from dataclasses import dataclass

from .dedup import DedupResult, DedupStatus
from .telemetry import Telemetry


@dataclass
class _BitmapWindow:
    max_seq: int
    bits: int = 0


class BitmapSlidingWindowDeduplicator:
    # same window semantics as SlidingWindowDeduplicator, but the
    # seen set is a plain int used as a bitmap. bit 0 is the oldest
    # seq in the window, bit W-1 is max_seq.
    def __init__(self, window_size: int = 32) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self._devices: dict[tuple[str, str], _BitmapWindow] = {}

    @property
    def devices_tracked(self) -> int:
        return len(self._devices)

    def _start(self, state: _BitmapWindow) -> int:
        return state.max_seq - self.window_size + 1

    def _pos(self, state: _BitmapWindow, seq: int) -> int:
        return seq - self._start(state)

    def _advance(self, state: _BitmapWindow, seq: int) -> None:
        delta = seq - state.max_seq
        if delta >= self.window_size:
            # jumped past the whole window, nothing survives
            state.bits = 0
        else:
            # drop the oldest delta bits, the rest slide down
            state.bits >>= delta
        state.max_seq = seq
        state.bits |= 1 << (self.window_size - 1)

    def check(self, telemetry: Telemetry) -> DedupResult:
        device_id = telemetry.device_id
        seq = telemetry.sequence
        boot_id = telemetry.boot_id
        key = (device_id, boot_id)
        state = self._devices.get(key)

        # brand new device session, only max_seq is set
        if state is None:
            self._devices[key] = _BitmapWindow(max_seq=seq, bits=1 << (self.window_size - 1))
            return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

        if seq > state.max_seq:
            # new high, slide window forward
            self._advance(state, seq)
            return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

        # fell behind the window, too late
        if seq < self._start(state):
            return DedupResult(DedupStatus.TOO_OLD, device_id, seq, boot_id)

        # inside the window, check the bit
        pos = self._pos(state, seq)
        if (state.bits >> pos) & 1:
            return DedupResult(DedupStatus.DUPLICATE, device_id, seq, boot_id)

        # arrived out of order but still in window
        state.bits |= 1 << pos
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

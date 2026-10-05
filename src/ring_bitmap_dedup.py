from __future__ import annotations

from dataclasses import dataclass, field

from .dedup import DedupResult, DedupStatus
from .telemetry import Telemetry


@dataclass
class _RingWindow:
    max_seq: int
    start_index: int = 0
    slots: bytearray = field(default_factory=bytearray)


class RingBitmapSlidingWindowDeduplicator:
    # same window semantics as the set and bitmap versions, but the
    # presence bits live in a fixed ring. slots never move, only
    # start_index does. a slot means nothing by itself, it only
    # means something together with the current window position.
    def __init__(self, window_size: int = 32) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self._devices: dict[tuple[str, str], _RingWindow] = {}

    @property
    def devices_tracked(self) -> int:
        return len(self._devices)

    def _window_start(self, state: _RingWindow) -> int:
        return state.max_seq - self.window_size + 1

    def _physical_index(self, state: _RingWindow, seq: int) -> int:
        logical_offset = seq - self._window_start(state)
        return (state.start_index + logical_offset) % self.window_size

    def _advance(self, state: _RingWindow, seq: int) -> None:
        delta = seq - state.max_seq
        if delta >= self.window_size:
            # jumped past the whole window, wipe everything
            state.slots = bytearray(self.window_size)
            state.start_index = 0
        else:
            # clear the slots of the seqs leaving the window,
            # then rotate the logical start forward
            for i in range(delta):
                state.slots[(state.start_index + i) % self.window_size] = 0
            state.start_index = (state.start_index + delta) % self.window_size
        state.max_seq = seq
        state.slots[self._physical_index(state, seq)] = 1

    def check(self, telemetry: Telemetry) -> DedupResult:
        device_id = telemetry.device_id
        seq = telemetry.sequence
        boot_id = telemetry.boot_id
        key = (device_id, boot_id)
        state = self._devices.get(key)

        # brand new device session, max sits at the last slot
        if state is None:
            state = _RingWindow(max_seq=seq, start_index=0, slots=bytearray(self.window_size))
            state.slots[self._physical_index(state, seq)] = 1
            self._devices[key] = state
            return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

        if seq > state.max_seq:
            # new high, slide window forward without moving any bits
            self._advance(state, seq)
            return DedupResult(DedupStatus.NEW, device_id, seq, boot_id)

        # fell behind the window, too late
        # (checked before touching any slot, so reused slots
        # can never fake a duplicate for evicted seqs)
        if seq < self._window_start(state):
            return DedupResult(DedupStatus.TOO_OLD, device_id, seq, boot_id)

        # inside the window, check the slot
        physical_index = self._physical_index(state, seq)
        if state.slots[physical_index]:
            return DedupResult(DedupStatus.DUPLICATE, device_id, seq, boot_id)

        # arrived out of order but still in window
        state.slots[physical_index] = 1
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

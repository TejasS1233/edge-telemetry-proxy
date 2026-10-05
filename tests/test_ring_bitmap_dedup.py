from __future__ import annotations

import random
import time

from src.bitmap_dedup import BitmapSlidingWindowDeduplicator
from src.dedup import DedupStatus, SlidingWindowDeduplicator
from src.ring_bitmap_dedup import RingBitmapSlidingWindowDeduplicator
from src.telemetry import Telemetry


def make_event(device: str = "dev-1", seq: int = 1, boot: str = "") -> Telemetry:
    return Telemetry(device_id=device, sequence=seq, timestamp=time.time(), metric="temperature", value=20.0, boot_id=boot)


def test_first_event_is_new():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW


def test_sequential_events_are_new():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW


def test_duplicate():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=100)).status == DedupStatus.DUPLICATE


def test_out_of_order_new():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=103))
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW


def test_out_of_order_duplicate():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=103))
    dedup.check(make_event(seq=102))
    assert dedup.check(make_event(seq=102)).status == DedupStatus.DUPLICATE


def test_too_old():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=99)).status == DedupStatus.TOO_OLD


def test_window_advancement_by_one():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=3)
    for seq in (1, 2, 3):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=4)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=2)).status == DedupStatus.DUPLICATE


def test_window_advancement_by_multiple():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 102):
        dedup.check(make_event(seq=seq))
    # jump 3 ahead, window becomes [101, 105]
    assert dedup.check(make_event(seq=105)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=100)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=101)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=104)).status == DedupStatus.NEW


def test_advancement_bigger_than_window():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=3)
    for seq in (10, 11, 12):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=50)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=12)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=49)).status == DedupStatus.NEW


def test_slot_reuse_after_slide():
    # window=5, take 100-104, then 105 steals 100's slot
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=105)).status == DedupStatus.NEW
    # evicted 100 must read TOO_OLD, not DUPLICATE off the reused slot
    assert dedup.check(make_event(seq=100)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=105)).status == DedupStatus.DUPLICATE
    for seq in (101, 102, 103, 104):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.DUPLICATE


def test_reused_slot_no_false_duplicate():
    # the nasty case: slot of an evicted seq is 1 again for a new seq.
    # asking for the evicted seq must say TOO_OLD, and asking for
    # an unseen in-window seq sharing no slot history must say NEW.
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=3)
    for seq in (1, 2, 3):
        dedup.check(make_event(seq=seq))
    dedup.check(make_event(seq=4))  # slot of 1 now means 4
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=4)).status == DedupStatus.DUPLICATE
    dedup.check(make_event(seq=5))  # slot of 2 now means 5
    dedup.check(make_event(seq=6))  # slot of 3 now means 6
    assert dedup.check(make_event(seq=2)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=3)).status == DedupStatus.TOO_OLD
    for seq in (4, 5, 6):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.DUPLICATE


def test_gaps_supported():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=110))
    assert dedup.check(make_event(seq=107)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=101)).status == DedupStatus.TOO_OLD


def test_boot_id_isolation():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 102):
        assert dedup.check(make_event(seq=seq, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=0, boot="boot-B")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=0, boot="boot-B")).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=100, boot="boot-A")).status == DedupStatus.DUPLICATE


def test_same_seq_across_boots():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=50, boot="boot-B")).status == DedupStatus.NEW


def test_window_size_one():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=1)
    assert dedup.check(make_event(seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=2)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD


def test_reset():
    dedup = RingBitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(device="a", seq=1))
    dedup.check(make_event(device="b", seq=1))
    dedup.reset("a")
    assert dedup.check(make_event(device="a", seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(device="b", seq=1)).status == DedupStatus.DUPLICATE
    dedup.reset()
    assert dedup.check(make_event(device="b", seq=1)).status == DedupStatus.NEW


def test_parity_with_existing_implementations():
    baseline = SlidingWindowDeduplicator(window_size=5)
    bitmap = BitmapSlidingWindowDeduplicator(window_size=5)
    ring = RingBitmapSlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 103, 103, 102, 105, 99, 105):
        expected = baseline.check(make_event(seq=seq)).status
        assert bitmap.check(make_event(seq=seq)).status == expected
        assert ring.check(make_event(seq=seq)).status == expected


def test_differential_fuzz_against_both():
    rng = random.Random(99)
    for trial in range(30):
        window_size = rng.choice([1, 2, 3, 5, 8, 32])
        impls = [
            SlidingWindowDeduplicator(window_size=window_size),
            BitmapSlidingWindowDeduplicator(window_size=window_size),
            RingBitmapSlidingWindowDeduplicator(window_size=window_size),
        ]
        for _ in range(500):
            event = make_event(
                device=rng.choice(["x", "y", "z"]),
                seq=rng.randrange(0, 30) if rng.random() < 0.7 else rng.randrange(0, 300),
                boot=rng.choice(["", "A", "B"]),
            )
            results = [impl.check(event) for impl in impls]
            assert results[1].status == results[0].status
            assert results[2].status == results[0].status
            assert results[2].sequence == results[0].sequence
            assert results[2].device_id == results[0].device_id
            assert results[2].boot_id == results[0].boot_id

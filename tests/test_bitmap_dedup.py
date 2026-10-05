from __future__ import annotations

import time

import pytest

from src.bitmap_dedup import BitmapSlidingWindowDeduplicator
from src.dedup import DedupStatus
from src.telemetry import Telemetry


def make_event(device: str = "dev-1", seq: int = 1, boot: str = "") -> Telemetry:
    return Telemetry(device_id=device, sequence=seq, timestamp=time.time(), metric="temperature", value=20.0, boot_id=boot)


def test_first_event_is_new():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW


def test_sequential_events_are_new():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW


def test_duplicate():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=100)).status == DedupStatus.DUPLICATE


def test_out_of_order_new():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=103))
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW


def test_out_of_order_duplicate():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=103))
    dedup.check(make_event(seq=102))
    assert dedup.check(make_event(seq=102)).status == DedupStatus.DUPLICATE


def test_too_old():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=99)).status == DedupStatus.TOO_OLD


def test_window_advancement_keeps_valid_bits():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 103):
        dedup.check(make_event(seq=seq))
    # window [99, 103], slide to [100, 104]
    assert dedup.check(make_event(seq=104)).status == DedupStatus.NEW
    # 101 and 103 survived the slide, 102 never arrived
    assert dedup.check(make_event(seq=101)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=103)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW


def test_advancement_larger_than_window():
    dedup = BitmapSlidingWindowDeduplicator(window_size=3)
    for seq in (10, 11, 12):
        dedup.check(make_event(seq=seq))
    # jump clears everything, window becomes [18, 20]
    assert dedup.check(make_event(seq=20)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=12)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=19)).status == DedupStatus.NEW


def test_gaps_supported():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=110))
    assert dedup.check(make_event(seq=107)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=101)).status == DedupStatus.TOO_OLD


def test_reboot_with_new_boot_is_new():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 102):
        assert dedup.check(make_event(seq=seq, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=0, boot="boot-B")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=0, boot="boot-B")).status == DedupStatus.DUPLICATE


def test_same_seq_different_boots():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=50, boot="boot-B")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.DUPLICATE


def test_window_size_one():
    dedup = BitmapSlidingWindowDeduplicator(window_size=1)
    assert dedup.check(make_event(seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=2)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD


def test_invalid_window_size():
    with pytest.raises(ValueError):
        BitmapSlidingWindowDeduplicator(window_size=0)


def test_reset_single_boot():
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=1, boot="boot-A"))
    dedup.check(make_event(seq=1, boot="boot-B"))
    dedup.reset("dev-1", "boot-A")
    assert dedup.check(make_event(seq=1, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1, boot="boot-B")).status == DedupStatus.DUPLICATE


def test_matches_baseline_on_spec_example():
    # 100 NEW, 101 NEW, 103 NEW, 103 DUP, 102 NEW, 105 NEW
    dedup = BitmapSlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=101)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=103)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=103)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=105)).status == DedupStatus.NEW

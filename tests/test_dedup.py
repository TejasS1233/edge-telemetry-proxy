from __future__ import annotations

import time

import pytest

from src.dedup import DedupStatus, SlidingWindowDeduplicator
from src.pipeline import Decision, EdgePipeline
from src.telemetry import Telemetry


def make_event(device: str = "dev-1", seq: int = 1, boot: str = "") -> Telemetry:
    return Telemetry(device_id=device, sequence=seq, timestamp=time.time(), metric="temperature", value=20.0, boot_id=boot)


def test_sequential_events_are_new():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        result = dedup.check(make_event(seq=seq))
        assert result.status == DedupStatus.NEW
        assert result.sequence == seq
        assert result.device_id == "dev-1"


def test_first_event_always_new():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=999)).status == DedupStatus.NEW


def test_immediate_duplicate():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=100)).status == DedupStatus.DUPLICATE


def test_spec_example():
    # 100 NEW, 101 NEW, 103 NEW, 102 NEW, 103 DUP, 104 NEW
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=101)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=103)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=103)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=104)).status == DedupStatus.NEW


def test_out_of_order_inside_window_is_new():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 103):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW
    # 102 shows up late but still counts
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW


def test_naive_rule_would_fail_this_case():
    # 102 < 103 but it was never seen, so NEW not DUPLICATE
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=103))
    assert dedup.check(make_event(seq=102)).status == DedupStatus.NEW


def test_gap_fill_is_new():
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100))
    dedup.check(make_event(seq=105))
    for seq in (101, 102, 103, 104):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW


def test_sequence_gaps_do_not_break_window():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=100)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=110)).status == DedupStatus.NEW
    # window is [106, 110] now
    assert dedup.check(make_event(seq=101)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=107)).status == DedupStatus.NEW


def test_too_old_after_window_advances():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=99)).status == DedupStatus.TOO_OLD


def test_window_advancement_evicts_oldest():
    dedup = SlidingWindowDeduplicator(window_size=3)
    for seq in (1, 2, 3):
        assert dedup.check(make_event(seq=seq)).status == DedupStatus.NEW
    # 4 pushes 1 out
    assert dedup.check(make_event(seq=4)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=2)).status == DedupStatus.DUPLICATE


def test_window_size_one():
    dedup = SlidingWindowDeduplicator(window_size=1)
    assert dedup.check(make_event(seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=2)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.TOO_OLD


def test_duplicate_after_window_advancement_is_too_old_not_duplicate():
    dedup = SlidingWindowDeduplicator(window_size=3)
    for seq in (10, 11, 12):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=15)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=10)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=10)).status == DedupStatus.TOO_OLD


def test_boundary_sequence_is_still_valid():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        dedup.check(make_event(seq=seq))
    assert dedup.check(make_event(seq=100)).status == DedupStatus.DUPLICATE
    dedup.check(make_event(seq=105))
    assert dedup.check(make_event(seq=100)).status == DedupStatus.TOO_OLD


def test_multiple_devices_independent_state():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(device="a", seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(device="b", seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(device="a", seq=1)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(device="b", seq=1)).status == DedupStatus.DUPLICATE
    # push a way ahead, b should not care
    for seq in range(2, 50):
        dedup.check(make_event(device="a", seq=seq))
    assert dedup.check(make_event(device="a", seq=1)).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(device="b", seq=2)).status == DedupStatus.NEW


def test_reset_single_device():
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(device="a", seq=1))
    dedup.check(make_event(device="b", seq=1))
    dedup.reset("a")
    assert dedup.check(make_event(device="a", seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(device="b", seq=1)).status == DedupStatus.DUPLICATE


def test_invalid_window_size():
    with pytest.raises(ValueError):
        SlidingWindowDeduplicator(window_size=0)


def test_pipeline_decisions():
    pipe = EdgePipeline(window_size=5)
    assert pipe.process(make_event(seq=100)).decision == Decision.FORWARD
    assert pipe.process(make_event(seq=100)).decision == Decision.DROP
    for seq in range(101, 110):
        pipe.process(make_event(seq=seq))
    assert pipe.process(make_event(seq=100)).decision == Decision.DROP


def test_sequential_within_one_boot():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 103):
        assert dedup.check(make_event(seq=seq, boot="boot-A")).status == DedupStatus.NEW


def test_duplicate_within_one_boot():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=10, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=10, boot="boot-A")).status == DedupStatus.DUPLICATE


def test_out_of_order_within_one_boot():
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=100, boot="boot-A"))
    dedup.check(make_event(seq=103, boot="boot-A"))
    assert dedup.check(make_event(seq=102, boot="boot-A")).status == DedupStatus.NEW


def test_too_old_within_one_boot():
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in range(100, 105):
        dedup.check(make_event(seq=seq, boot="boot-A"))
    assert dedup.check(make_event(seq=99, boot="boot-A")).status == DedupStatus.TOO_OLD


def test_reboot_with_new_boot_id_is_new():
    # 100, 101, 102 then reboot, counter resets to 0
    dedup = SlidingWindowDeduplicator(window_size=5)
    for seq in (100, 101, 102):
        assert dedup.check(make_event(seq=seq, boot="boot-A")).status == DedupStatus.NEW
    # same device, new boot, low seq must not read as TOO_OLD
    assert dedup.check(make_event(seq=0, boot="boot-B")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1, boot="boot-B")).status == DedupStatus.NEW


def test_same_seq_different_boots_is_new():
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=50, boot="boot-B")).status == DedupStatus.NEW
    # and each session still dupes its own repeats
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=50, boot="boot-B")).status == DedupStatus.DUPLICATE


def test_boots_keep_independent_windows():
    dedup = SlidingWindowDeduplicator(window_size=3)
    for seq in (10, 11, 12):
        dedup.check(make_event(seq=seq, boot="boot-A"))
    # slide boot-A far ahead, boot-B should not care
    assert dedup.check(make_event(seq=50, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=10, boot="boot-A")).status == DedupStatus.TOO_OLD
    assert dedup.check(make_event(seq=10, boot="boot-B")).status == DedupStatus.NEW


def test_missing_boot_id_stays_compatible():
    # old events without boot_id share one session per device
    dedup = SlidingWindowDeduplicator(window_size=5)
    assert dedup.check(make_event(seq=1)).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1)).status == DedupStatus.DUPLICATE
    assert dedup.check(make_event(seq=1, boot="boot-A")).status == DedupStatus.NEW


def test_reset_clears_all_boots_of_device():
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=1, boot="boot-A"))
    dedup.check(make_event(seq=1, boot="boot-B"))
    dedup.reset("dev-1")
    assert dedup.check(make_event(seq=1, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1, boot="boot-B")).status == DedupStatus.NEW


def test_reset_single_boot_only():
    dedup = SlidingWindowDeduplicator(window_size=5)
    dedup.check(make_event(seq=1, boot="boot-A"))
    dedup.check(make_event(seq=1, boot="boot-B"))
    dedup.reset("dev-1", "boot-A")
    assert dedup.check(make_event(seq=1, boot="boot-A")).status == DedupStatus.NEW
    assert dedup.check(make_event(seq=1, boot="boot-B")).status == DedupStatus.DUPLICATE

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .dedup import DedupResult, DedupStatus, SlidingWindowDeduplicator
from .telemetry import Telemetry


class Decision(str, Enum):
    FORWARD = "FORWARD"
    DROP = "DROP"


@dataclass(frozen=True, slots=True)
class PipelineResult:
    telemetry: Telemetry
    dedup: DedupResult
    decision: Decision


class PipelineStage(Protocol):
    def process(self, telemetry: Telemetry, result: PipelineResult | None) -> PipelineResult | None:
        ...  # pragma: no cover


class EdgePipeline:
    def __init__(self, deduplicator: SlidingWindowDeduplicator | None = None, window_size: int = 32) -> None:
        self.deduplicator = deduplicator or SlidingWindowDeduplicator(window_size=window_size)
        self._extra_stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> None:
        self._extra_stages.append(stage)

    def process(self, telemetry: Telemetry) -> PipelineResult:
        dedup = self.deduplicator.check(telemetry)
        # only fresh stuff goes up, rest gets dropped
        decision = Decision.FORWARD if dedup.status == DedupStatus.NEW else Decision.DROP
        result = PipelineResult(telemetry=telemetry, dedup=dedup, decision=decision)
        for stage in self._extra_stages:
            updated = stage.process(telemetry, result)
            if updated is not None:
                result = updated
        return result

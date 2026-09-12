from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SpanKind(StrEnum):
    AGENT_RUN = "agent.run"
    AGENT_STEP = "agent.step"
    LLM = "gen_ai.chat"
    TOOL = "tool.call"
    RETRIEVAL = "retrieval"
    EVALUATION = "evaluation"


class SpanStatus(StrEnum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: UUID = Field(default_factory=uuid4)
    span_id: UUID = Field(default_factory=uuid4)
    parent_span_id: UUID | None = None
    tenant_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    kind: SpanKind
    name: str = Field(min_length=1, max_length=256)
    status: SpanStatus = SpanStatus.UNSET
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[TraceEvent] = Field(default_factory=list)
    schema_version: str = "1.0"

    def finish(self, status: SpanStatus = SpanStatus.OK) -> TraceSpan:
        self.ended_at = datetime.now(timezone.utc)
        self.status = status
        return self

    @property
    def duration_ms(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() * 1000

    def add_event(self, name: str, **attributes: Any) -> TraceEvent:
        event = TraceEvent(name=name, attributes=attributes)
        self.events.append(event)
        return event

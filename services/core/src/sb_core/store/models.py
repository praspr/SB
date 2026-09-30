"""Signal and sync-state dataclass models for core.db."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Signal:
    id: int
    source: str
    source_id: str
    kind: str
    occurred_at: str  # ISO UTC string
    title: str
    body: Optional[str]
    scope: Optional[str]
    verb: Optional[str]
    refs: list  # decoded JSON list
    raw_ref: Optional[str]
    created_at: str


@dataclass
class SyncState:
    adapter: str
    last_run_at: str
    signal_count: int
    error: Optional[str]

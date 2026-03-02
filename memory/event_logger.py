"""Simple in-memory trace logger for explainability."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RequestTrace:
    request_id: int
    utterance: str
    timestamp: float
    considered_rules: list[dict[str, Any]] = field(default_factory=list)
    applied_rules: list[dict[str, Any]] = field(default_factory=list)
    outcome: str | None = None
    episode_id: str | None = None


class EventLogger:
    def __init__(self):
        self._request_id = 0
        self._current_trace: RequestTrace | None = None
        self._last_trace: RequestTrace | None = None

    def start_request(self, utterance: str, timestamp: float) -> int:
        self._request_id += 1
        self._current_trace = RequestTrace(
            request_id=self._request_id,
            utterance=utterance,
            timestamp=timestamp,
        )
        return self._request_id

    def log_rule_consideration(self, rule_hash: str, metadata: dict[str, Any] | None = None) -> None:
        if self._current_trace is None:
            return
        self._current_trace.considered_rules.append(
            {
                "rule_hash": rule_hash,
                "metadata": metadata or {},
            }
        )

    def log_rule_application(self, rule_hash: str, success: bool, reason: str = "") -> None:
        if self._current_trace is None:
            return
        self._current_trace.applied_rules.append(
            {
                "rule_hash": rule_hash,
                "success": success,
                "reason": reason,
            }
        )

    def finish_request(self, outcome: str, episode_id: str | None = None) -> None:
        if self._current_trace is None:
            return
        self._current_trace.outcome = outcome
        self._current_trace.episode_id = episode_id
        self._last_trace = self._current_trace
        self._current_trace = None

    def get_last_trace(self) -> dict[str, Any]:
        if self._last_trace is None:
            return {}
        return deepcopy(
            {
                "request_id": self._last_trace.request_id,
                "utterance": self._last_trace.utterance,
                "timestamp": self._last_trace.timestamp,
                "considered_rules": self._last_trace.considered_rules,
                "applied_rules": self._last_trace.applied_rules,
                "outcome": self._last_trace.outcome,
                "episode_id": self._last_trace.episode_id,
            }
        )

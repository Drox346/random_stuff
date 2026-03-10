"""Core datatypes and canonicalization helpers."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from .constants import CONTEXT_WHITELIST, DEFAULT_WORKSPACE_MODE

RuleStatus = Literal["candidate", "active", "blocked"]
EpisodeType = Literal["attempt", "correction"]
ScalarValue: TypeAlias = str | bool | int | float


def _normalize_scalar(value: ScalarValue) -> ScalarValue:
    if isinstance(value, str):
        return normalize_identifier(value)
    return value


def normalize_identifier(value: str) -> str:
    """Normalize free-text entity identifiers for deterministic matching."""
    return "_".join(value.strip().lower().split())


def display_count_bucket(display_count: int) -> str:
    if display_count <= 1:
        return "1"
    if display_count == 2:
        return "2"
    return "3+"


def canonicalize_entities(entities: dict[str, str] | None) -> dict[str, str]:
    entities = entities or {}
    normalized = {
        normalize_identifier(str(k)): normalize_identifier(str(v))
        for k, v in entities.items()
        if k is not None and v is not None
    }
    return dict(sorted(normalized.items(), key=lambda item: item[0]))


def canonicalize_action(action: dict[str, ScalarValue] | None) -> dict[str, ScalarValue]:
    action = action or {}
    normalized = {
        normalize_identifier(str(key)): _normalize_scalar(value)
        for key, value in action.items()
        if key is not None and value is not None
    }
    return dict(sorted(normalized.items(), key=lambda item: item[0]))


def canonicalize_context(context: dict[str, str | int] | None) -> dict[str, str | int]:
    context = context or {}
    canonical: dict[str, str | int] = {}

    if "display_count_bucket" in context:
        canonical["display_count_bucket"] = str(context["display_count_bucket"])
    elif "display_count" in context:
        canonical["display_count_bucket"] = display_count_bucket(int(context["display_count"]))

    workspace_mode = context.get("workspace_mode", DEFAULT_WORKSPACE_MODE)
    canonical["workspace_mode"] = normalize_identifier(str(workspace_mode))

    filtered = {k: v for k, v in canonical.items() if k in CONTEXT_WHITELIST}
    return dict(sorted(filtered.items(), key=lambda item: item[0]))


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class PlannedAction:
    intent: str
    entities: dict[str, str]
    action: dict[str, ScalarValue]
    context: dict[str, str | int]
    timestamp: float
    role: str | None = None

    def __post_init__(self) -> None:
        self.intent = normalize_identifier(self.intent)
        self.entities = canonicalize_entities(self.entities)
        self.action = canonicalize_action(self.action)
        self.context = canonicalize_context(self.context)
        if self.role:
            self.role = normalize_identifier(self.role)

    def canonical_dict(self) -> dict[str, Any]:
        payload = {
            "intent": normalize_identifier(self.intent),
            "entities": canonicalize_entities(self.entities),
            "action": canonicalize_action(self.action),
            "context": canonicalize_context(self.context),
            "timestamp": float(self.timestamp),
        }
        if self.role:
            payload["role"] = normalize_identifier(self.role)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self.canonical_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannedAction":
        return cls(
            intent=str(data["intent"]),
            entities=dict(data.get("entities", {})),
            action=dict(data.get("action", {})),
            context=dict(data.get("context", {})),
            timestamp=float(data.get("timestamp", time.time())),
            role=data.get("role"),
        )


@dataclass(slots=True)
class CorrectionRecord:
    original: PlannedAction
    corrected: PlannedAction
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original.to_dict(),
            "corrected": self.corrected.to_dict(),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CorrectionRecord":
        return cls(
            original=PlannedAction.from_dict(dict(data["original"])),
            corrected=PlannedAction.from_dict(dict(data["corrected"])),
            timestamp=float(data["timestamp"]),
        )


@dataclass(slots=True)
class RuleKey:
    intent: str
    entities: dict[str, str]
    role: str | None
    context: dict[str, str | int]

    def __post_init__(self) -> None:
        self.intent = normalize_identifier(self.intent)
        self.entities = canonicalize_entities(self.entities)
        self.context = canonicalize_context(self.context)
        if self.role:
            self.role = normalize_identifier(self.role)

    def canonical_dict(self) -> dict[str, Any]:
        payload = {
            "intent": normalize_identifier(self.intent),
            "entities": canonicalize_entities(self.entities),
            "context": canonicalize_context(self.context),
        }
        if self.role:
            payload["role"] = normalize_identifier(self.role)
        return payload

    def hash(self) -> str:
        payload = canonical_json(self.canonical_dict()).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleKey":
        return cls(
            intent=str(data["intent"]),
            entities=dict(data.get("entities", {})),
            role=data.get("role"),
            context=dict(data.get("context", {})),
        )


@dataclass(slots=True)
class RuleValue:
    preferences: dict[str, ScalarValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.preferences = canonicalize_action(self.preferences)

    def to_preferences(self) -> dict[str, ScalarValue]:
        return canonicalize_action(self.preferences)

    @classmethod
    def from_preferences(cls, data: dict[str, Any]) -> "RuleValue":
        return cls(preferences=canonicalize_action(data))


def compute_candidate_id(rule_key_hash: str, rule_value: RuleValue) -> str:
    payload = f"{rule_key_hash}:{canonical_json(rule_value.to_preferences())}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(slots=True)
class PreferenceCandidate:
    candidate_id: str
    rule_key_hash: str
    rule_key: RuleKey
    rule_value: RuleValue
    positive_count: int = 0
    negative_count: int = 0
    last_seen: float = 0.0
    status: RuleStatus = "candidate"
    source_episode_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "rule_key_hash": self.rule_key_hash,
            "rule_key": self.rule_key.canonical_dict(),
            "rule_value": self.rule_value.to_preferences(),
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "last_seen": self.last_seen,
            "status": self.status,
            "source_episode_ids": list(self.source_episode_ids),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreferenceCandidate":
        return cls(
            candidate_id=str(data["candidate_id"]),
            rule_key_hash=str(data["rule_key_hash"]),
            rule_key=RuleKey.from_dict(dict(data["rule_key"])),
            rule_value=RuleValue.from_preferences(dict(data["rule_value"])),
            positive_count=int(data.get("positive_count", 0)),
            negative_count=int(data.get("negative_count", 0)),
            last_seen=float(data.get("last_seen", 0.0)),
            status=data.get("status", "candidate"),
            source_episode_ids=list(data.get("source_episode_ids", [])),
            confidence=float(data.get("confidence", 0.0)),
        )


@dataclass(slots=True)
class Episode:
    episode_id: str
    episode_type: EpisodeType
    timestamp: float
    planned_action: dict[str, Any] | None
    original_action: dict[str, Any] | None
    corrected_action: dict[str, Any] | None
    outcome: str
    linked_episode_id: str | None = None
    matched_rule_hashes: list[str] = field(default_factory=list)
    snippet_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "episode_type": self.episode_type,
            "timestamp": self.timestamp,
            "planned_action": self.planned_action,
            "original_action": self.original_action,
            "corrected_action": self.corrected_action,
            "outcome": self.outcome,
            "linked_episode_id": self.linked_episode_id,
            "matched_rule_hashes": list(self.matched_rule_hashes),
            "snippet_text": self.snippet_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        return cls(
            episode_id=str(data["episode_id"]),
            episode_type=data["episode_type"],
            timestamp=float(data["timestamp"]),
            planned_action=data.get("planned_action"),
            original_action=data.get("original_action"),
            corrected_action=data.get("corrected_action"),
            outcome=str(data.get("outcome", "unknown")),
            linked_episode_id=data.get("linked_episode_id"),
            matched_rule_hashes=list(data.get("matched_rule_hashes", [])),
            snippet_text=str(data.get("snippet_text", "")),
        )


@dataclass(slots=True)
class MatchExplanation:
    snippet_text: str
    matched_rule_hashes: list[str]
    matched_rules: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "snippet_text": self.snippet_text,
            "matched_rule_hashes": list(self.matched_rule_hashes),
            "matched_rules": list(self.matched_rules),
        }

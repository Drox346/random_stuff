"""Core datatypes and canonicalization helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from .constants import CONTEXT_WHITELIST, DEFAULT_WORKSPACE_MODE

RuleStatus = Literal["candidate", "active", "blocked"]


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
class SemanticParse:
    intent: str
    entities: dict[str, str]
    role: str
    context: dict[str, str | int]
    raw_utterance: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "entities": dict(self.entities),
            "role": self.role,
            "context": dict(self.context),
            "raw_utterance": self.raw_utterance,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class RuleKey:
    intent: str
    entities: dict[str, str]
    role: str
    context: dict[str, str | int]

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "intent": normalize_identifier(self.intent),
            "entities": canonicalize_entities(self.entities),
            "role": normalize_identifier(self.role),
            "context": canonicalize_context(self.context),
        }

    def hash(self) -> str:
        payload = canonical_json(self.canonical_dict()).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleKey":
        return cls(
            intent=str(data["intent"]),
            entities=dict(data.get("entities", {})),
            role=str(data["role"]),
            context=dict(data.get("context", {})),
        )


@dataclass(slots=True)
class RuleValue:
    window_state: str | None = None
    always_on_top: bool | None = None
    display: str | None = None
    size_preset: str | None = None
    dock_region: str | None = None
    visibility: str | None = None

    def to_desired_state(self) -> dict[str, Any]:
        desired: dict[str, Any] = {}
        if self.window_state is not None:
            desired["window_state"] = self.window_state
        if self.always_on_top is not None:
            desired["always_on_top"] = self.always_on_top
        if self.display is not None:
            desired["display"] = self.display
        if self.size_preset is not None:
            desired["size_preset"] = self.size_preset
        if self.dock_region is not None:
            desired["dock_region"] = self.dock_region
        if self.visibility is not None:
            desired["visibility"] = self.visibility
        return desired

    @classmethod
    def from_desired_state(cls, data: dict[str, Any]) -> "RuleValue":
        return cls(
            window_state=data.get("window_state"),
            always_on_top=data.get("always_on_top"),
            display=data.get("display"),
            size_preset=data.get("size_preset"),
            dock_region=data.get("dock_region"),
            visibility=data.get("visibility"),
        )


def compute_candidate_id(rule_key_hash: str, rule_value: RuleValue) -> str:
    payload = f"{rule_key_hash}:{canonical_json(rule_value.to_desired_state())}".encode("utf-8")
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
            "rule_value": self.rule_value.to_desired_state(),
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
            rule_value=RuleValue.from_desired_state(dict(data["rule_value"])),
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
    timestamp: float
    user_utterance: str
    parsed_intent: str
    parsed_entities: dict[str, str]
    target_role: str
    context_signature: dict[str, str | int]
    actions_executed: list[dict[str, Any]]
    outcome: str
    linked_episode_id: str | None = None
    considered_rule_hashes: list[str] = field(default_factory=list)
    applied_rule_hashes: list[str] = field(default_factory=list)
    auto_desired_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "timestamp": self.timestamp,
            "user_utterance": self.user_utterance,
            "parsed_intent": self.parsed_intent,
            "parsed_entities": dict(self.parsed_entities),
            "target_role": self.target_role,
            "context_signature": dict(self.context_signature),
            "actions_executed": list(self.actions_executed),
            "outcome": self.outcome,
            "linked_episode_id": self.linked_episode_id,
            "considered_rule_hashes": list(self.considered_rule_hashes),
            "applied_rule_hashes": list(self.applied_rule_hashes),
            "auto_desired_state": dict(self.auto_desired_state),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        return cls(
            episode_id=str(data["episode_id"]),
            timestamp=float(data["timestamp"]),
            user_utterance=str(data["user_utterance"]),
            parsed_intent=str(data["parsed_intent"]),
            parsed_entities=dict(data.get("parsed_entities", {})),
            target_role=str(data["target_role"]),
            context_signature=dict(data.get("context_signature", {})),
            actions_executed=list(data.get("actions_executed", [])),
            outcome=str(data.get("outcome", "unknown")),
            linked_episode_id=data.get("linked_episode_id"),
            considered_rule_hashes=list(data.get("considered_rule_hashes", [])),
            applied_rule_hashes=list(data.get("applied_rule_hashes", [])),
            auto_desired_state=dict(data.get("auto_desired_state", {})),
        )


@dataclass(slots=True)
class PolicyDecision:
    desired_state: dict[str, Any]
    considered_rule_hashes: list[str]
    applied_rule_hashes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "desired_state": dict(self.desired_state),
            "considered_rule_hashes": list(self.considered_rule_hashes),
            "applied_rule_hashes": list(self.applied_rule_hashes),
        }

"""Render active preference rules into a system-prompt snippet."""

from __future__ import annotations

from typing import Any

from .constants import (
    CONSISTENT_CONFIDENCE_THRESHOLD,
    CONSISTENT_SUPPORT_THRESHOLD,
    STRONG_CONFIDENCE_THRESHOLD,
    STRONG_SUPPORT_THRESHOLD,
    USUAL_CONFIDENCE_THRESHOLD,
    USUAL_SUPPORT_THRESHOLD,
)
from .models import PreferenceCandidate


class PromptSnippetBuilder:
    def build(self, candidates: list[PreferenceCandidate]) -> tuple[str, list[dict[str, Any]]]:
        ordered = self._order_candidates(candidates)
        rendered: list[str] = []
        details: list[dict[str, Any]] = []

        for candidate in ordered:
            band = self._strength_band(candidate)
            if band is None:
                continue
            line = self._render_candidate(candidate, band)
            if not line:
                continue
            rendered.append(f"- {line}")
            details.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "rule_key": candidate.rule_key.canonical_dict(),
                    "rule_value": candidate.rule_value.to_preferences(),
                    "positive_count": candidate.positive_count,
                    "negative_count": candidate.negative_count,
                    "confidence": candidate.confidence,
                    "strength": band,
                }
            )

        if not rendered:
            return "", []

        snippet = "\n".join(
            [
                "The system includes a memory module that tracks patterns in the user's corrections.",
                "Use these learned preferences only when they directly apply to the current action.",
                "Do not generalize beyond the specific cases listed.",
                "",
                "Current learned user preferences:",
                *rendered,
                "",
                "When responding or choosing defaults, prefer these behaviors unless the user explicitly requests something different.",
            ]
        )
        return snippet, details

    def _order_candidates(self, candidates: list[PreferenceCandidate]) -> list[PreferenceCandidate]:
        return sorted(
            candidates,
            key=lambda candidate: (
                len(candidate.rule_key.context),
                len(candidate.rule_key.entities),
                candidate.confidence,
                candidate.last_seen,
                candidate.candidate_id,
            ),
            reverse=True,
        )

    def _strength_band(self, candidate: PreferenceCandidate) -> str | None:
        support = candidate.positive_count + candidate.negative_count
        confidence = candidate.confidence
        if confidence >= STRONG_CONFIDENCE_THRESHOLD and support >= STRONG_SUPPORT_THRESHOLD:
            return "strong"
        if confidence >= CONSISTENT_CONFIDENCE_THRESHOLD and support >= CONSISTENT_SUPPORT_THRESHOLD:
            return "consistent"
        if confidence >= USUAL_CONFIDENCE_THRESHOLD and support >= USUAL_SUPPORT_THRESHOLD:
            return "usual"
        return None

    def _render_candidate(
        self,
        candidate: PreferenceCandidate,
        band: str,
    ) -> str:
        preferences = candidate.rule_value.to_preferences()
        if len(preferences) != 1:
            parts = [self._positive_phrase(self._subject(candidate.rule_key.entities), key, value, band) for key, value in preferences.items()]
            return " ".join(part for part in parts if part)

        action_key, preferred_value = next(iter(preferences.items()))
        subject = self._subject(candidate.rule_key.entities)

        return self._positive_phrase(subject, action_key, preferred_value, band)

    def _positive_phrase(self, subject: str, action_key: str, value: Any, band: str) -> str:
        if band == "strong":
            return f"The user always wants {subject} to {self._action_phrase(action_key, value)}."
        return f"The user {self._band_word(band)} prefers {subject} to {self._action_phrase(action_key, value)}."

    def _band_word(self, band: str) -> str:
        if band == "consistent":
            return "consistently"
        if band == "usual":
            return "usually"
        return "always"

    def _subject(self, entities: dict[str, str]) -> str:
        if "widget_id" in entities:
            return f"'{entities['widget_id']}'"
        if "app" in entities:
            return f"'{entities['app']}'"
        if "panel" in entities:
            return f"'{entities['panel']}'"
        if "widget_group" in entities:
            return f"all {entities['widget_group'].replace('_', ' ')} widgets"
        if entities:
            first_key, first_value = next(iter(entities.items()))
            return f"{first_key.replace('_', ' ')} '{first_value}'"
        return "this action"

    def _action_phrase(self, action_key: str, value: Any) -> str:
        text_value = str(value).replace("_", " ")
        if action_key in {"window_state", "presentation"}:
            if text_value == "fullscreen":
                return "open in fullscreen"
            if text_value in {"widget", "panel", "modal"}:
                article = "an" if text_value[0] in "aeiou" else "a"
                return f"open as {article} {text_value}"
            return f"open with {action_key.replace('_', ' ')} {text_value}"
        if action_key == "placement":
            return f"open at the {text_value}"
        if action_key == "display":
            return f"open on the {text_value} display"
        if action_key == "always_on_top":
            return "stay always on top" if bool(value) else "not stay always on top"
        return f"use {action_key.replace('_', ' ')} {text_value}"

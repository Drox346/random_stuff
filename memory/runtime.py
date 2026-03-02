"""Orchestrates semantic parsing, policy lookup, UI application, and learning."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .event_logger import EventLogger
from .memory_store import MemoryStore
from .models import Episode, PolicyDecision, SemanticParse
from .policy_engine import PolicyEngine
from .preference_learner import PreferenceLearner
from .semantic_resolver import SemanticResolver
from .ui_adapter import MockDynamicUIAdapter, UICapabilityAdapter


class PreferenceMemoryRuntime:
    def __init__(
        self,
        data_dir: str | Path | None = None,
        store: MemoryStore | None = None,
        resolver: SemanticResolver | None = None,
        learner: PreferenceLearner | None = None,
        policy_engine: PolicyEngine | None = None,
        adapter: UICapabilityAdapter | None = None,
        event_logger: EventLogger | None = None,
    ):
        self.store = store or MemoryStore(data_dir=data_dir)
        self.resolver = resolver or SemanticResolver()
        self.learner = learner or PreferenceLearner(self.store)
        self.policy_engine = policy_engine or PolicyEngine(self.store)
        self.adapter = adapter or MockDynamicUIAdapter()
        self.event_logger = event_logger or EventLogger()
        self._last_explanation: dict[str, Any] = {}

    def reset(self) -> None:
        self.store.clear()
        self._last_explanation = {}

    def process_utterance(
        self,
        utterance: str,
        runtime_context: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        parse = self.resolver.resolve(utterance, runtime_context=runtime_context, timestamp=timestamp)
        self.event_logger.start_request(utterance=parse.raw_utterance, timestamp=parse.timestamp)

        if self.learner.is_correction(parse):
            response = self._handle_correction(parse)
        else:
            response = self._handle_base_request(parse)

        self.event_logger.finish_request(outcome=response["outcome"], episode_id=response["episode_id"])
        return response

    def explain_last_action(self) -> dict[str, Any]:
        if not self._last_explanation:
            return {
                "message": "No action has been processed yet.",
                "trace": self.event_logger.get_last_trace(),
            }
        explanation = dict(self._last_explanation)
        explanation["trace"] = self.event_logger.get_last_trace()
        return explanation

    def _handle_base_request(self, parse: SemanticParse) -> dict[str, Any]:
        handle, base_action = self._execute_base_intent(parse)
        actions = [base_action]
        ui_object = self.adapter.resolve(parse.role, parse.entities, handle=handle)

        decision = self.policy_engine.decide(parse)
        for rule_hash in decision.considered_rule_hashes:
            self.event_logger.log_rule_consideration(rule_hash)

        policy_success = True
        policy_actions: list[dict[str, Any]] = []
        if decision.desired_state and ui_object is not None:
            policy_actions, policy_success = self._apply_desired_state(ui_object, decision.desired_state)
            actions.extend(policy_actions)

        if decision.applied_rule_hashes:
            for rule_hash in decision.applied_rule_hashes:
                self.event_logger.log_rule_application(rule_hash, success=policy_success)

        outcome = "success" if base_action["success"] and policy_success else "failure"
        episode_id = self._new_episode_id()
        episode = Episode(
            episode_id=episode_id,
            timestamp=parse.timestamp,
            user_utterance=parse.raw_utterance,
            parsed_intent=parse.intent,
            parsed_entities=parse.entities,
            target_role=parse.role,
            context_signature=parse.context,
            actions_executed=actions,
            outcome=outcome,
            linked_episode_id=None,
            considered_rule_hashes=decision.considered_rule_hashes,
            applied_rule_hashes=decision.applied_rule_hashes,
            auto_desired_state=decision.desired_state,
        )
        self.store.add_episode(episode)
        self._set_last_explanation(decision)

        return {
            "episode_id": episode_id,
            "intent": parse.intent,
            "outcome": outcome,
            "ui_object": ui_object,
            "policy": decision.to_dict(),
            "actions": actions,
        }

    def _handle_correction(self, parse: SemanticParse) -> dict[str, Any]:
        target_episode = self.learner.link_correction_episode(parse)
        episode_id = self._new_episode_id()
        actions: list[dict[str, Any]] = []
        success = False
        updates: dict[str, Any] = {"updated_candidates": [], "negative_updates": []}

        if target_episode is not None:
            target_ui_object = self._extract_ui_object(target_episode)
            if target_ui_object is None:
                target_ui_object = self.adapter.resolve(
                    target_episode.target_role,
                    target_episode.parsed_entities,
                    handle=None,
                )
            desired_state = self.learner.correction_to_rule_value(parse).to_desired_state()
            if target_ui_object is not None and desired_state:
                actions, success = self._apply_desired_state(target_ui_object, desired_state)
            if success:
                updates = self.learner.record_correction(
                    target_episode=target_episode,
                    correction=parse,
                    success=True,
                    correction_episode_id=episode_id,
                )

        outcome = "success" if success else "failure"
        episode = Episode(
            episode_id=episode_id,
            timestamp=parse.timestamp,
            user_utterance=parse.raw_utterance,
            parsed_intent=parse.intent,
            parsed_entities=parse.entities,
            target_role=parse.role,
            context_signature=parse.context,
            actions_executed=actions,
            outcome=outcome,
            linked_episode_id=target_episode.episode_id if target_episode else None,
        )
        self.store.add_episode(episode)
        self._last_explanation = {
            "message": "Correction processed",
            "linked_episode_id": episode.linked_episode_id,
            "learning_updates": updates,
        }

        return {
            "episode_id": episode_id,
            "intent": parse.intent,
            "outcome": outcome,
            "linked_episode_id": episode.linked_episode_id,
            "actions": actions,
            "learning_updates": updates,
        }

    def _execute_base_intent(self, parse: SemanticParse) -> tuple[str | None, dict[str, Any]]:
        if parse.intent == "open_app":
            app_id = parse.entities.get("app", "unknown_app")
            handle = self.adapter.open_app(app_id)
            return handle, {
                "op": "open_app",
                "entity": app_id,
                "success": True,
                "handle": handle,
            }

        if parse.intent == "open_document":
            doc_ref = parse.entities.get("doc_ref", "unknown_document")
            handle = self.adapter.open_document(doc_ref)
            return handle, {
                "op": "open_document",
                "entity": doc_ref,
                "success": True,
                "handle": handle,
            }

        if parse.intent == "show_panel":
            panel_id = parse.entities.get("panel", "unknown_panel")
            handle = self.adapter.show_panel(panel_id)
            return handle, {
                "op": "show_panel",
                "entity": panel_id,
                "success": True,
                "handle": handle,
            }

        if parse.intent in {"open_settings", "run_tool"}:
            return None, {
                "op": parse.intent,
                "entity": parse.entities,
                "success": True,
                "handle": None,
            }

        return None, {
            "op": parse.intent,
            "entity": parse.entities,
            "success": False,
            "handle": None,
        }

    def _apply_desired_state(
        self,
        ui_object: str,
        desired_state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool]:
        actions: list[dict[str, Any]] = []
        all_success = True

        for key, value in desired_state.items():
            success = False
            op_name = ""
            if key == "window_state":
                op_name = "set_window_state"
                success = self.adapter.set_window_state(ui_object, str(value))
            elif key == "display":
                op_name = "move_to_display"
                success = self.adapter.move_to_display(ui_object, str(value))
            elif key == "size_preset":
                op_name = "resize_preset"
                success = self.adapter.resize_preset(ui_object, str(value))
            elif key == "dock_region":
                op_name = "dock"
                success = self.adapter.dock(ui_object, str(value))
            elif key == "visibility":
                op_name = "set_visibility"
                set_visibility = getattr(self.adapter, "set_visibility", None)
                success = bool(set_visibility and set_visibility(ui_object, str(value)))
            elif key == "always_on_top":
                op_name = "set_always_on_top"
                setter = getattr(self.adapter, "set_always_on_top", None)
                success = bool(setter and setter(ui_object, bool(value)))

            actions.append(
                {
                    "op": op_name,
                    "value": value,
                    "ui_object": ui_object,
                    "success": success,
                }
            )
            if not success:
                all_success = False

        return actions, all_success

    def _extract_ui_object(self, episode: Episode) -> str | None:
        for action in reversed(episode.actions_executed):
            ui_object = action.get("ui_object")
            if ui_object:
                return str(ui_object)
        return None

    def _set_last_explanation(self, decision: PolicyDecision) -> None:
        if not decision.applied_rule_hashes:
            self._last_explanation = {
                "message": "No preference rule applied.",
                "considered_rule_hashes": decision.considered_rule_hashes,
                "applied_rule_hashes": [],
            }
            return

        selected_rule_id = decision.applied_rule_hashes[0]
        candidate = self.store.get_candidate_by_id(selected_rule_id)
        if not candidate:
            self._last_explanation = {
                "message": "Applied rule missing from store.",
                "applied_rule_hashes": decision.applied_rule_hashes,
            }
            return

        self._last_explanation = {
            "matched_rule_key": candidate.rule_key.canonical_dict(),
            "matched_rule_value": candidate.rule_value.to_desired_state(),
            "confidence": candidate.confidence,
            "positive_count": candidate.positive_count,
            "negative_count": candidate.negative_count,
            "source_episode_ids": list(candidate.source_episode_ids),
            "considered_rule_hashes": decision.considered_rule_hashes,
            "applied_rule_hashes": decision.applied_rule_hashes,
        }

    def _new_episode_id(self) -> str:
        return uuid.uuid4().hex

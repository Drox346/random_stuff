"""Rule-based semantic resolver for demo utterances."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import (
    DEFAULT_WORKSPACE_MODE,
    ROLE_MODAL_DIALOG,
    ROLE_PANEL,
    ROLE_PRIMARY_WINDOW,
)
from .models import SemanticParse, canonicalize_context, canonicalize_entities, display_count_bucket, normalize_identifier


class SemanticResolver:
    def resolve(
        self,
        utterance: str,
        runtime_context: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> SemanticParse:
        runtime_context = runtime_context or {}
        timestamp = float(timestamp if timestamp is not None else time.time())
        raw = utterance.strip()
        text = raw.lower().strip()

        intent = "unknown"
        role = ROLE_PRIMARY_WINDOW
        entities: dict[str, str] = {}

        open_app_match = re.match(r"^(?:open|launch)\s+(?:program|app)\s+(.+)$", text)
        open_doc_match = re.match(r"^open\s+document\s+(.+)$", text)
        show_panel_match = re.match(r"^show\s+panel\s+(.+)$", text)
        open_settings_match = re.match(r"^open\s+settings(?:\s+(.+))?$", text)
        run_tool_match = re.match(r"^run\s+tool\s+(.+)$", text)

        move_display_match = re.match(r"^(?:move\s+it|move)\s+to\s+display\s+(\d+|primary)$", text)
        resize_match = re.match(r"^(?:make\s+it\s+)?size\s+(small|medium|large)$", text)
        dock_match = re.match(r"^(?:dock\s+(?:it\s+)?)?(left|right|bottom|floating)$", text)
        show_hide_panel_match = re.match(r"^(show|hide)\s+panel(?:\s+(.+))?$", text)
        always_on_top_match = re.match(r"^(?:set\s+)?always\s+on\s+top\s+(on|off)$", text)

        if open_app_match:
            intent = "open_app"
            entities = {"app": normalize_identifier(open_app_match.group(1))}
            role = ROLE_PRIMARY_WINDOW
        elif open_doc_match:
            intent = "open_document"
            doc_ref = normalize_identifier(open_doc_match.group(1))
            entities = {"doc_ref": doc_ref}
            if "." in doc_ref:
                entities["doc_type"] = normalize_identifier(doc_ref.rsplit(".", maxsplit=1)[-1])
            role = ROLE_PRIMARY_WINDOW
        elif show_panel_match:
            intent = "show_panel"
            entities = {"panel": normalize_identifier(show_panel_match.group(1))}
            role = ROLE_PANEL
        elif open_settings_match:
            intent = "open_settings"
            scope = open_settings_match.group(1) or "global"
            entities = {"scope": normalize_identifier(scope)}
            role = ROLE_MODAL_DIALOG
        elif run_tool_match:
            intent = "run_tool"
            entities = {"tool_name": normalize_identifier(run_tool_match.group(1))}
            role = ROLE_PRIMARY_WINDOW
        elif "fullscreen" in text and any(keyword in text for keyword in ("make", "go", "enter", "fullscreen")):
            intent = "set_window_state"
            role = ROLE_PRIMARY_WINDOW
            entities = {
                "window_state": "normal"
                if any(keyword in text for keyword in ("exit", "leave", "stop", "off"))
                else "fullscreen"
            }
        elif "maximize" in text:
            intent = "set_window_state"
            role = ROLE_PRIMARY_WINDOW
            entities = {
                "window_state": "normal"
                if any(keyword in text for keyword in ("exit", "leave", "unmaximize"))
                else "maximized"
            }
        elif move_display_match:
            intent = "set_display"
            role = ROLE_PRIMARY_WINDOW
            entities = {"display": normalize_identifier(move_display_match.group(1))}
        elif resize_match:
            intent = "set_size_preset"
            role = ROLE_PRIMARY_WINDOW
            entities = {"size_preset": normalize_identifier(resize_match.group(1))}
        elif dock_match:
            intent = "set_dock_region"
            role = ROLE_PANEL
            entities = {"dock_region": normalize_identifier(dock_match.group(1))}
        elif show_hide_panel_match:
            intent = "set_visibility"
            role = ROLE_PANEL
            action, panel_name = show_hide_panel_match.groups()
            entities = {
                "visibility": "shown" if action == "show" else "hidden",
            }
            if panel_name:
                entities["panel"] = normalize_identifier(panel_name)
        elif always_on_top_match:
            intent = "set_always_on_top"
            role = ROLE_PRIMARY_WINDOW
            entities = {"always_on_top": "true" if always_on_top_match.group(1) == "on" else "false"}

        context = self._build_context(runtime_context)
        return SemanticParse(
            intent=intent,
            entities=canonicalize_entities(entities),
            role=role,
            context=context,
            raw_utterance=raw,
            timestamp=timestamp,
        )

    def _build_context(self, runtime_context: dict[str, Any]) -> dict[str, str | int]:
        display_count = int(runtime_context.get("display_count", 1))
        workspace_mode = normalize_identifier(str(runtime_context.get("workspace_mode", DEFAULT_WORKSPACE_MODE)))
        context = {
            "display_count_bucket": display_count_bucket(display_count),
            "workspace_mode": workspace_mode,
        }
        return canonicalize_context(context)

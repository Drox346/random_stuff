"""Constants for the preference memory demo."""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
EPISODES_FILE = "episodes.json"
PREFERENCE_CANDIDATES_FILE = "preference_candidates.json"

CORRECTION_WINDOW_SECONDS = 90
PROMOTION_POSITIVE_THRESHOLD = 2
PROMOTION_MARGIN_THRESHOLD = 2
DISABLE_NEGATIVE_THRESHOLD = 2

CONTEXT_WHITELIST = ("display_count_bucket", "workspace_mode")
DEFAULT_WORKSPACE_MODE = "default"

ROLE_PRIMARY_WINDOW = "primary_window"
ROLE_PANEL = "panel"
ROLE_MODAL_DIALOG = "modal_dialog"
ROLE_EDITOR_SURFACE = "editor_surface"
ROLE_PREVIEW_SURFACE = "preview_surface"

CORRECTION_INTENTS = {
    "set_window_state",
    "set_display",
    "set_size_preset",
    "set_dock_region",
    "set_visibility",
    "set_always_on_top",
}

BASE_INTENTS = {
    "open_app",
    "open_document",
    "show_panel",
    "open_settings",
    "run_tool",
}

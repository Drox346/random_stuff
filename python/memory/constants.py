"""Constants for the structured preference memory service."""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
EPISODES_FILE = "episodes.json"
PREFERENCE_CANDIDATES_FILE = "preference_candidates.json"

CORRECTION_WINDOW_SECONDS = 90
PROMOTION_POSITIVE_THRESHOLD = 2
PROMOTION_MARGIN_THRESHOLD = 2
DISABLE_NEGATIVE_THRESHOLD = 2

STRONG_CONFIDENCE_THRESHOLD = 0.90
STRONG_SUPPORT_THRESHOLD = 5
CONSISTENT_CONFIDENCE_THRESHOLD = 0.75
CONSISTENT_SUPPORT_THRESHOLD = 3
USUAL_CONFIDENCE_THRESHOLD = 0.60
USUAL_SUPPORT_THRESHOLD = 2

CONTEXT_WHITELIST = ("display_count_bucket", "workspace_mode")
DEFAULT_WORKSPACE_MODE = "default"

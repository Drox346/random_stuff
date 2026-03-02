"""JSON-backed persistence for episodes and preference candidates."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .constants import DATA_DIR, EPISODES_FILE, PREFERENCE_CANDIDATES_FILE
from .models import Episode, PreferenceCandidate, RuleValue


class MemoryStore:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.episodes_path = self.data_dir / EPISODES_FILE
        self.candidates_path = self.data_dir / PREFERENCE_CANDIDATES_FILE
        self._ensure_file(self.episodes_path)
        self._ensure_file(self.candidates_path)

    def _ensure_file(self, path: Path) -> None:
        if not path.exists():
            path.write_text("[]", encoding="utf-8")

    def _read_json_list(self, path: Path) -> list[dict]:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError(f"Expected list payload in {path}")
        return payload

    def _write_json_atomic(self, path: Path, payload: list[dict]) -> None:
        fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def clear(self) -> None:
        self._write_json_atomic(self.episodes_path, [])
        self._write_json_atomic(self.candidates_path, [])

    def list_episodes(self) -> list[Episode]:
        records = [Episode.from_dict(row) for row in self._read_json_list(self.episodes_path)]
        return sorted(records, key=lambda record: record.timestamp)

    def add_episode(self, episode: Episode) -> None:
        records = self._read_json_list(self.episodes_path)
        records.append(episode.to_dict())
        self._write_json_atomic(self.episodes_path, records)

    def get_episode(self, episode_id: str) -> Episode | None:
        for episode in self.list_episodes():
            if episode.episode_id == episode_id:
                return episode
        return None

    def list_candidates(self) -> list[PreferenceCandidate]:
        records = [PreferenceCandidate.from_dict(row) for row in self._read_json_list(self.candidates_path)]
        return sorted(records, key=lambda record: (record.last_seen, record.candidate_id))

    def upsert_candidate(self, candidate: PreferenceCandidate) -> None:
        records = self._read_json_list(self.candidates_path)
        updated = False
        for idx, row in enumerate(records):
            if row.get("candidate_id") == candidate.candidate_id:
                records[idx] = candidate.to_dict()
                updated = True
                break
        if not updated:
            records.append(candidate.to_dict())
        self._write_json_atomic(self.candidates_path, records)

    def get_candidate_by_id(self, candidate_id: str) -> PreferenceCandidate | None:
        for candidate in self.list_candidates():
            if candidate.candidate_id == candidate_id:
                return candidate
        return None

    def find_candidate(self, rule_key_hash: str, rule_value: RuleValue) -> PreferenceCandidate | None:
        desired_state = rule_value.to_desired_state()
        for candidate in self.list_candidates():
            if candidate.rule_key_hash != rule_key_hash:
                continue
            if candidate.rule_value.to_desired_state() == desired_state:
                return candidate
        return None

    def get_active_preferences(self) -> list[PreferenceCandidate]:
        return [candidate for candidate in self.list_candidates() if candidate.status == "active"]

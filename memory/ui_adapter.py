"""UI capability adapter interface and fully mocked dynamic implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import count
from typing import Any

from .constants import ROLE_PANEL, ROLE_PRIMARY_WINDOW


class UICapabilityAdapter(ABC):
    @abstractmethod
    def open_app(self, app_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def open_document(self, doc_ref: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def show_panel(self, panel_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, role: str, entity: dict[str, str], handle: str | None = None) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def set_window_state(self, ui_object: str, state: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def move_to_display(self, ui_object: str, display_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def resize_preset(self, ui_object: str, preset: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def dock(self, ui_object: str, region: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self, ui_object: str) -> set[str]:
        raise NotImplementedError


class MockDynamicUIAdapter(UICapabilityAdapter):
    def __init__(self):
        self._id_counter = count(1)
        self._objects: dict[str, dict[str, Any]] = {}
        self._app_to_window: dict[str, str] = {}
        self._doc_to_window: dict[str, str] = {}
        self._latest_window_by_app: dict[str, str] = {}
        self._latest_panel_by_name: dict[str, str] = {}
        self._last_primary_window: str | None = None
        self._last_panel: str | None = None

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{next(self._id_counter)}"

    def _register_object(self, object_id: str, payload: dict[str, Any]) -> None:
        self._objects[object_id] = payload

    def open_app(self, app_id: str) -> str:
        app_handle = self._new_id("app_inst")
        window_id = self._new_id("win")
        self._register_object(
            app_handle,
            {
                "type": "app_instance",
                "app": app_id,
                "window": window_id,
                "capabilities": set(),
            },
        )
        self._register_object(
            window_id,
            {
                "type": "primary_window",
                "app": app_id,
                "state": "normal",
                "display": "primary",
                "size_preset": "medium",
                "always_on_top": False,
                "capabilities": {"set_window_state", "move_to_display", "resize_preset", "set_always_on_top"},
            },
        )
        self._app_to_window[app_handle] = window_id
        self._latest_window_by_app[app_id] = window_id
        self._last_primary_window = window_id
        return app_handle

    def open_document(self, doc_ref: str) -> str:
        doc_handle = self._new_id("doc_inst")
        window_id = self._new_id("win")
        self._register_object(
            doc_handle,
            {
                "type": "document_instance",
                "doc_ref": doc_ref,
                "window": window_id,
                "capabilities": set(),
            },
        )
        self._register_object(
            window_id,
            {
                "type": "primary_window",
                "doc_ref": doc_ref,
                "state": "normal",
                "display": "primary",
                "size_preset": "medium",
                "always_on_top": False,
                "capabilities": {"set_window_state", "move_to_display", "resize_preset", "set_always_on_top"},
            },
        )
        self._doc_to_window[doc_handle] = window_id
        self._last_primary_window = window_id
        return doc_handle

    def show_panel(self, panel_id: str) -> str:
        panel_handle = self._new_id("panel")
        self._register_object(
            panel_handle,
            {
                "type": "panel",
                "panel": panel_id,
                "dock_region": "floating",
                "visibility": "shown",
                "size_preset": "medium",
                "capabilities": {"dock", "resize_preset", "set_visibility"},
            },
        )
        self._latest_panel_by_name[panel_id] = panel_handle
        self._last_panel = panel_handle
        return panel_handle

    def resolve(self, role: str, entity: dict[str, str], handle: str | None = None) -> str | None:
        if role == ROLE_PRIMARY_WINDOW:
            if handle and handle in self._app_to_window:
                return self._app_to_window[handle]
            if handle and handle in self._doc_to_window:
                return self._doc_to_window[handle]
            app = entity.get("app")
            if app and app in self._latest_window_by_app:
                return self._latest_window_by_app[app]
            return self._last_primary_window

        if role == ROLE_PANEL:
            if handle and self._objects.get(handle, {}).get("type") == "panel":
                return handle
            panel_name = entity.get("panel")
            if panel_name and panel_name in self._latest_panel_by_name:
                return self._latest_panel_by_name[panel_name]
            return self._last_panel

        return None

    def _supports(self, ui_object: str, capability: str) -> bool:
        metadata = self._objects.get(ui_object)
        if metadata is None:
            return False
        return capability in metadata.get("capabilities", set())

    def set_window_state(self, ui_object: str, state: str) -> bool:
        if not self._supports(ui_object, "set_window_state"):
            return False
        self._objects[ui_object]["state"] = state
        return True

    def move_to_display(self, ui_object: str, display_id: str) -> bool:
        if not self._supports(ui_object, "move_to_display"):
            return False
        self._objects[ui_object]["display"] = str(display_id)
        return True

    def resize_preset(self, ui_object: str, preset: str) -> bool:
        if not self._supports(ui_object, "resize_preset"):
            return False
        self._objects[ui_object]["size_preset"] = preset
        return True

    def dock(self, ui_object: str, region: str) -> bool:
        if not self._supports(ui_object, "dock"):
            return False
        self._objects[ui_object]["dock_region"] = region
        return True

    def set_visibility(self, ui_object: str, visibility: str) -> bool:
        if not self._supports(ui_object, "set_visibility"):
            return False
        self._objects[ui_object]["visibility"] = visibility
        return True

    def set_always_on_top(self, ui_object: str, enabled: bool) -> bool:
        if not self._supports(ui_object, "set_always_on_top"):
            return False
        self._objects[ui_object]["always_on_top"] = bool(enabled)
        return True

    def get_capabilities(self, ui_object: str) -> set[str]:
        metadata = self._objects.get(ui_object)
        if not metadata:
            return set()
        return set(metadata.get("capabilities", set()))

    def get_object_snapshot(self, ui_object: str) -> dict[str, Any]:
        metadata = self._objects.get(ui_object, {})
        snapshot = dict(metadata)
        if "capabilities" in snapshot:
            snapshot["capabilities"] = sorted(snapshot["capabilities"])
        return snapshot

"""Problem binary sensors for hafleet, one per task kind."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HafleetConfigEntry
from .const import KNOWN_KINDS
from .entity import HafleetEntity
from .hub import HafleetHub

KIND_RE = re.compile(r"^[a-z0-9_]{1,64}$")
SEVERITIES = ("critical", "warning", "info")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HafleetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a sensor per task kind hafleet reports and remove kinds it no longer reports."""
    hub = entry.runtime_data
    registry = er.async_get(hass)
    known: set[str] = set()
    prefix = f"{entry.entry_id}_kind_"

    @callback
    def sync_kinds() -> None:
        if hub.payload is None:
            return
        kinds = {k for k in hub.kinds if KIND_RE.match(k)}
        if new := kinds - known:
            known.update(new)
            async_add_entities(KindProblemSensor(hub, entry, k) for k in sorted(new))
        for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
            if (
                reg.domain == Platform.BINARY_SENSOR
                and reg.unique_id.startswith(prefix)
                and reg.unique_id.removeprefix(prefix) not in kinds
            ):
                known.discard(reg.unique_id.removeprefix(prefix))
                registry.async_remove(reg.entity_id)

    sync_kinds()
    entry.async_on_unload(hub.async_add_listener(sync_kinds))


class KindProblemSensor(HafleetEntity, BinarySensorEntity):
    """On while hafleet reports an unacknowledged task of this kind."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: HafleetHub, entry: ConfigEntry, kind: str) -> None:
        super().__init__(hub, entry, f"kind_{kind}")
        self.kind = kind
        if kind in KNOWN_KINDS:
            self._attr_translation_key = kind
        else:
            self._attr_name = kind.replace("_", " ").capitalize()

    def _data(self) -> dict[str, Any]:
        return self.hub.kinds.get(self.kind, {})

    @property
    def available(self) -> bool:
        return super().available and self.kind in self.hub.kinds

    @property
    def is_on(self) -> bool:
        count = self._data().get("count")
        return isinstance(count, int) and count > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._data()
        tasks = data.get("tasks")
        out = []
        for t in tasks if isinstance(tasks, list) else []:
            if isinstance(t, dict) and isinstance(t.get("title"), str):
                out.append(
                    {
                        "title": t["title"],
                        "severity": t.get("severity") if t.get("severity") in SEVERITIES else None,
                        "acknowledged": t.get("acknowledged") is True,
                    }
                )
        count = data.get("count")
        sev = data.get("max_severity")
        return {
            "count": count if isinstance(count, int) else 0,
            "max_severity": sev if sev in SEVERITIES else None,
            "tasks": out,
        }

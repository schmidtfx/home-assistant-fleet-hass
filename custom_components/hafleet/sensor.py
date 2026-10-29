"""Sensors for hafleet: open tasks, last sync and connection state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HafleetConfigEntry
from .entity import HafleetEntity

SEVERITIES = ("critical", "warning", "info")
CONNECTION_STATES = ["connected", "connecting", "error", "disabled"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HafleetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_add_entities(
        [
            OpenTasksSensor(hub, entry, "open_tasks"),
            LastSyncSensor(hub, entry, "last_sync"),
            ConnectionSensor(hub, entry, "connection"),
        ]
    )


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class OpenTasksSensor(HafleetEntity, SensorEntity):
    """Number of open (unacknowledged) tasks."""

    _attr_translation_key = "open_tasks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _open(self) -> dict[str, Any]:
        open_ = (self.hub.payload or {}).get("open")
        return open_ if isinstance(open_, dict) else {}

    @property
    def native_value(self) -> int | None:
        return _int(self._open().get("total"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        open_ = self._open()
        return {k: _int(open_.get(k)) for k in (*SEVERITIES, "acknowledged")}


class LastSyncSensor(HafleetEntity, SensorEntity):
    """When hafleet last read all data from this instance."""

    _attr_translation_key = "last_sync"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        value = (self.hub.payload or {}).get("last_sync")
        return dt_util.parse_datetime(value) if isinstance(value, str) else None


class ConnectionSensor(HafleetEntity, SensorEntity):
    """hafleet's connection state to this instance, with sync warnings."""

    _attr_translation_key = "connection"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = CONNECTION_STATES
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        state = (self.hub.payload or {}).get("state")
        return state if state in CONNECTION_STATES else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        warnings = (self.hub.payload or {}).get("warnings")
        if not isinstance(warnings, list):
            warnings = []
        return {"warnings": [w for w in warnings if isinstance(w, str)]}

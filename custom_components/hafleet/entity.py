"""Base entity for hafleet."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .hub import HafleetHub


class HafleetEntity(Entity):
    """An entity on the hafleet device, updated from the hub."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: HafleetHub, entry: ConfigEntry, key: str) -> None:
        self.hub = hub
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="hafleet",
            manufacturer="hafleet",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://github.com/schmidtfx/home-assistant-fleet",
        )

    @property
    def available(self) -> bool:
        return self.hub.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.async_add_listener(self.async_write_ha_state))

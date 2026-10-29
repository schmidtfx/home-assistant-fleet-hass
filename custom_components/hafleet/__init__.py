"""The hafleet integration: shows hafleet's view of this instance as entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_USER_ID
from .hub import HafleetHub

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type HafleetConfigEntry = ConfigEntry[HafleetHub]


async def async_setup_entry(hass: HomeAssistant, entry: HafleetConfigEntry) -> bool:
    """Set up hafleet from a config entry."""
    hub = HafleetHub(hass, entry.entry_id, entry.data[CONF_USER_ID])
    await hub.async_load()
    entry.runtime_data = hub
    entry.async_on_unload(hub.async_start())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HafleetConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: HafleetConfigEntry) -> None:
    """Delete the saved status when the entry is removed."""
    await HafleetHub(hass, entry.entry_id, entry.data[CONF_USER_ID]).async_remove()

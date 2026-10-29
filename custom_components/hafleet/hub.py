"""Receives hafleet_status events and keeps the latest status."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_HEARTBEAT_SECONDS,
    DOMAIN,
    EVENT_STATUS,
    SCHEMA_VERSION,
    STALE_HEARTBEATS,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

SAVE_DELAY = 10
STALE_CHECK_INTERVAL = timedelta(minutes=1)


class HafleetHub:
    """Latest status from hafleet, persisted so entities survive a restart.

    Event data is untrusted input: it is validated loosely and only read with
    type checks, and only events fired by the configured user are accepted.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, user_id: str) -> None:
        self._hass = hass
        self._user_id = user_id
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self._listeners: list[Callable[[], None]] = []
        self.payload: dict[str, Any] | None = None
        self.received_at: datetime | None = None
        self.enabled = True
        self._was_available = False

    async def async_load(self) -> None:
        """Load the last status saved before a restart."""
        data = await self._store.async_load()
        if not data:
            return
        received_at = dt_util.parse_datetime(data.get("received_at") or "")
        if isinstance(data.get("payload"), dict) and received_at is not None:
            self.payload = data["payload"]
            self.received_at = received_at
            self.enabled = bool(data.get("enabled", True))
        self._was_available = self.available

    async def async_remove(self) -> None:
        """Delete the saved status."""
        await self._store.async_remove()

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Listen for status events and check staleness. Returns the stop callback."""
        unsub_event = self._hass.bus.async_listen(EVENT_STATUS, self._handle_event)
        unsub_timer = async_track_time_interval(self._hass, self._check_stale, STALE_CHECK_INTERVAL)

        @callback
        def stop() -> None:
            unsub_event()
            unsub_timer()

        return stop

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        """Call update whenever the status or its availability changes."""
        self._listeners.append(update)

        @callback
        def remove() -> None:
            self._listeners.remove(update)

        return remove

    @property
    def heartbeat(self) -> timedelta:
        seconds = (self.payload or {}).get("heartbeat_seconds")
        if not isinstance(seconds, int) or seconds <= 0:
            seconds = DEFAULT_HEARTBEAT_SECONDS
        return timedelta(seconds=seconds)

    @property
    def available(self) -> bool:
        """Whether hafleet reported recently and publishing is on."""
        if self.payload is None or self.received_at is None or not self.enabled:
            return False
        return dt_util.utcnow() - self.received_at < self.heartbeat * STALE_HEARTBEATS

    @property
    def kinds(self) -> dict[str, dict[str, Any]]:
        """Task kinds of the latest status, with their data."""
        kinds = (self.payload or {}).get("kinds")
        if not isinstance(kinds, dict):
            return {}
        return {k: v for k, v in kinds.items() if isinstance(k, str) and isinstance(v, dict)}

    @callback
    def _handle_event(self, event: Event) -> None:
        if event.context.user_id != self._user_id:
            _LOGGER.debug("Ignoring %s event from user %s", EVENT_STATUS, event.context.user_id)
            return
        data = event.data
        if data.get("schema") != SCHEMA_VERSION:
            _LOGGER.warning(
                "Ignoring %s event with schema %s; update the hafleet integration",
                EVENT_STATUS,
                data.get("schema"),
            )
            return
        self.received_at = dt_util.utcnow()
        if data.get("enabled") is False:
            self.enabled = False  # keep the last status; entities become unavailable
        else:
            self.enabled = True
            self.payload = dict(data)
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        self._notify()

    @callback
    def _check_stale(self, _now: datetime) -> None:
        if self.available != self._was_available:
            self._notify()

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "payload": self.payload,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "enabled": self.enabled,
        }

    @callback
    def _notify(self) -> None:
        self._was_available = self.available
        for update in list(self._listeners):
            update()

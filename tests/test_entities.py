"""Tests for hafleet entities driven by hafleet_status events."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.hafleet.const import CONF_USER_ID, DOMAIN, EVENT_STATUS

OPEN = "sensor.hafleet_open_tasks"
LAST_SYNC = "sensor.hafleet_last_sync"
CONNECTION = "sensor.hafleet_connection"
UPDATE = "binary_sensor.hafleet_updates_available"
BACKUP = "binary_sensor.hafleet_backup_stale"


def status(**overrides: Any) -> dict[str, Any]:
    """An event payload as hafleet's statusEvent builds it."""
    data = {
        "schema": 1,
        "enabled": True,
        "instance_id": "i1",
        "instance_name": "Home",
        "state": "connected",
        "warnings": ["backups: timeout"],
        "last_sync": "2026-10-29T10:00:00Z",
        "heartbeat_seconds": 300,
        "open": {"total": 1, "critical": 0, "warning": 0, "info": 1, "acknowledged": 1},
        "kinds": {
            "update": {
                "count": 1,
                "max_severity": "info",
                "tasks": [
                    {"title": "Core 2026.11", "severity": "info", "acknowledged": False},
                    {"title": "Mushroom", "severity": "info", "acknowledged": True},
                ],
            },
            "backup_stale": {"count": 0, "max_severity": None, "tasks": []},
        },
    }
    data.update(overrides)
    return data


@pytest.fixture
async def entry(hass: HomeAssistant, hass_admin_user) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_USER_ID: hass_admin_user.id})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def fire(hass: HomeAssistant, user_id: str | None, data: dict[str, Any]) -> None:
    hass.bus.async_fire(EVENT_STATUS, data, context=Context(user_id=user_id))
    await hass.async_block_till_done()


async def test_status_event_creates_entities(hass: HomeAssistant, entry, hass_admin_user) -> None:
    assert hass.states.get(OPEN).state == STATE_UNAVAILABLE  # nothing received yet
    assert hass.states.get(UPDATE) is None

    await fire(hass, hass_admin_user.id, status())

    open_ = hass.states.get(OPEN)
    assert open_.state == "1"
    assert open_.attributes["info"] == 1 and open_.attributes["acknowledged"] == 1
    assert hass.states.get(LAST_SYNC).state == "2026-10-29T10:00:00+00:00"
    conn = hass.states.get(CONNECTION)
    assert conn.state == "connected" and conn.attributes["warnings"] == ["backups: timeout"]

    update = hass.states.get(UPDATE)
    assert update.state == STATE_ON
    assert update.attributes["count"] == 1 and update.attributes["max_severity"] == "info"
    assert [t["acknowledged"] for t in update.attributes["tasks"]] == [False, True]
    assert hass.states.get(BACKUP).state == STATE_OFF

    # Entities are first class: registered with unique IDs on one device.
    reg = er.async_get(hass)
    ids = {e.unique_id for e in er.async_entries_for_config_entry(reg, entry.entry_id)}
    assert f"{entry.entry_id}_open_tasks" in ids and f"{entry.entry_id}_kind_update" in ids
    assert len({e.device_id for e in er.async_entries_for_config_entry(reg, entry.entry_id)}) == 1


async def test_ignores_other_users_and_schemas(
    hass: HomeAssistant, entry, hass_admin_user, hass_read_only_user
) -> None:
    await fire(hass, hass_read_only_user.id, status())
    await fire(hass, None, status())
    await fire(hass, hass_admin_user.id, status(schema=2))
    assert hass.states.get(OPEN).state == STATE_UNAVAILABLE
    assert hass.states.get(UPDATE) is None


async def test_malformed_payload(hass: HomeAssistant, entry, hass_admin_user) -> None:
    await fire(hass, hass_admin_user.id, status(open="x", kinds={"update": "x", "Bad Kind!": {}}, warnings=None))
    assert hass.states.get(OPEN).state == "unknown"
    assert hass.states.get(UPDATE) is None
    assert hass.states.get(CONNECTION).attributes["warnings"] == []


async def test_kind_removed_and_unknown_kind(hass: HomeAssistant, entry, hass_admin_user) -> None:
    await fire(hass, hass_admin_user.id, status())
    kinds = {"update": status()["kinds"]["update"], "future_kind": {"count": 2, "tasks": []}}
    await fire(hass, hass_admin_user.id, status(kinds=kinds))
    assert hass.states.get(BACKUP) is None
    assert er.async_get(hass).async_get(BACKUP) is None
    assert hass.states.get("binary_sensor.hafleet_future_kind").state == STATE_ON


async def test_disabled_event(hass: HomeAssistant, entry, hass_admin_user) -> None:
    await fire(hass, hass_admin_user.id, status())
    await fire(hass, hass_admin_user.id, {"schema": 1, "enabled": False})
    assert hass.states.get(OPEN).state == STATE_UNAVAILABLE
    assert hass.states.get(UPDATE).state == STATE_UNAVAILABLE
    await fire(hass, hass_admin_user.id, status())
    assert hass.states.get(OPEN).state == "1"


async def test_stale(hass: HomeAssistant, entry, hass_admin_user, freezer: FrozenDateTimeFactory) -> None:
    await fire(hass, hass_admin_user.id, status(heartbeat_seconds=60))
    freezer.tick(timedelta(seconds=150))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(OPEN).state == "1"
    freezer.tick(timedelta(seconds=60))  # 3 heartbeats without an event
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(OPEN).state == STATE_UNAVAILABLE
    assert hass.states.get(UPDATE).state == STATE_UNAVAILABLE


async def test_restored_after_restart(hass: HomeAssistant, hass_admin_user, hass_storage) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_USER_ID: hass_admin_user.id})
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{entry.entry_id}",
        "data": {"payload": status(), "received_at": dt_util.utcnow().isoformat(), "enabled": True},
    }
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(OPEN).state == "1"
    assert hass.states.get(UPDATE).state == STATE_ON


async def test_saves_status(hass: HomeAssistant, entry, hass_admin_user, hass_storage, freezer) -> None:
    await fire(hass, hass_admin_user.id, status())
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    saved = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]
    assert saved["payload"]["instance_name"] == "Home" and saved["enabled"] is True

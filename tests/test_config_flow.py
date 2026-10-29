"""Tests for the hafleet config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hafleet.const import CONF_USER_ID, DOMAIN


async def test_user_flow(hass: HomeAssistant, hass_admin_user) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    options = result["data_schema"].schema[CONF_USER_ID].config["options"]
    assert hass_admin_user.id in [o["value"] for o in options]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USER_ID: hass_admin_user.id})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_USER_ID: hass_admin_user.id}


async def test_single_instance(hass: HomeAssistant, hass_admin_user) -> None:
    MockConfigEntry(domain=DOMAIN, data={CONF_USER_ID: hass_admin_user.id}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"

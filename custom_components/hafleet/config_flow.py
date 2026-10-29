"""Config flow for hafleet."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .const import CONF_USER_ID, DOMAIN


class HafleetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick the Home Assistant user hafleet connects as."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        users = [u for u in await self.hass.auth.async_get_users() if u.is_active and not u.system_generated]
        if not users:
            return self.async_abort(reason="no_users")
        if user_input is not None:
            return self.async_create_entry(title="hafleet", data={CONF_USER_ID: user_input[CONF_USER_ID]})
        options = [SelectOptionDict(value=u.id, label=f"{u.name or 'Unnamed'} ({u.id})") for u in users]
        schema = vol.Schema(
            {
                vol.Required(CONF_USER_ID): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

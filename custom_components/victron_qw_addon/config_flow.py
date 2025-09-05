"""Config flow for Victron QW Addon integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_SLAVE_ID


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Victron QW Addon."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate and convert slave_id from text to int to avoid slider UI
            raw_slave = user_input.get(CONF_SLAVE_ID)
            try:
                slave_val = int(raw_slave)
                if slave_val < 1 or slave_val > 247:
                    errors[CONF_SLAVE_ID] = "invalid_slave_id"
                else:
                    user_input[CONF_SLAVE_ID] = slave_val
            except (TypeError, ValueError):
                errors[CONF_SLAVE_ID] = "invalid_slave_id"

            if not errors:
                # You can add validation for the IP address here if you want
                # For example, try to connect to the Cerbo GX.
                # For now, we'll just accept any string.
                return self.async_create_entry(title=user_input[CONF_IP_ADDRESS], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Required(CONF_SLAVE_ID, default="100"): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Victron QW Addon."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validate slave id textbox
            raw_slave = user_input.get(CONF_SLAVE_ID)
            try:
                slave_val = int(raw_slave)
                if slave_val < 1 or slave_val > 247:
                    errors[CONF_SLAVE_ID] = "invalid_slave_id"
                else:
                    user_input[CONF_SLAVE_ID] = slave_val
            except (TypeError, ValueError):
                errors[CONF_SLAVE_ID] = "invalid_slave_id"

            if not errors:
                return self.async_create_entry(title="Options", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_IP_ADDRESS,
                    default=self.config_entry.options.get(
                        CONF_IP_ADDRESS, self.config_entry.data.get(CONF_IP_ADDRESS, "")
                    ),
                ): cv.string,
                vol.Required(
                    CONF_SLAVE_ID,
                    default=str(
                        self.config_entry.options.get(
                            CONF_SLAVE_ID, self.config_entry.data.get(CONF_SLAVE_ID, 100)
                        )
                    ),
                ): cv.string,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)


@callback
def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return OptionsFlowHandler(config_entry)

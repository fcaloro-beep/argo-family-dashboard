from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .argo_client import ArgoFamilyClient, ArgoFamilyError
from .const import DEFAULT_NAME, DOMAIN


class ArgoFamilyDashboardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            unique = f"{user_input['school_code']}_{user_input[CONF_USERNAME]}_{user_input['child_name']}"
            await self.async_set_unique_id(unique.lower())
            self._abort_if_unique_id_configured()

            try:
                await ArgoFamilyClient(self.hass, user_input).async_get_dashboard()
            except ArgoFamilyError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Argo {user_input['child_name']}",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required("child_name"): str,
                vol.Required("school_code"): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ArgoFamilyDashboardOptionsFlow(config_entry)


class ArgoFamilyDashboardOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 30),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=360)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

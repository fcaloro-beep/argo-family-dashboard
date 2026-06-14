from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .argo_client import ArgoFamilyClient, ArgoFamilyError
from .const import DOMAIN


class ArgoFamilyDashboardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict | None = None
        self._students: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._students = await ArgoFamilyClient(
                    self.hass,
                    user_input,
                ).async_get_students()
            except ArgoFamilyError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                self._credentials = user_input
                if len(self._students) > 1:
                    return await self.async_step_student()
                student = self._students[0]
                return await self._async_create_student_entry(user_input, student)

        schema = vol.Schema(
            {
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

    async def async_step_student(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        credentials = self._credentials or {}
        students = self._students

        if user_input is not None:
            student = next(
                (
                    item
                    for item in students
                    if item["id"] == user_input["student_id"]
                ),
                None,
            )
            if student is None:
                errors["base"] = "unknown"
            else:
                data = {
                    **credentials,
                    "child_name": user_input.get("child_name") or student["name"],
                }
                return await self._async_create_student_entry(data, student)

        options = {
            item["id"]: f"{item['name']} ({item['index'] + 1})"
            for item in students
        }
        default_student = students[0] if students else {"id": "", "name": ""}
        schema = vol.Schema(
            {
                vol.Required(
                    "student_id",
                    default=default_student["id"],
                ): vol.In(options),
                vol.Optional(
                    "child_name",
                    default=default_student["name"],
                ): str,
            }
        )
        return self.async_show_form(
            step_id="student",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def _async_create_student_entry(
        self,
        data: dict,
        student: dict,
    ) -> FlowResult:
        entry_data = {
            **data,
            "child_name": data.get("child_name") or student["name"],
            "student_id": student["id"],
            "student_index": student["index"],
        }
        unique = (
            f"{entry_data['school_code']}_"
            f"{entry_data[CONF_USERNAME]}_"
            f"{entry_data['student_id']}"
        )
        await self.async_set_unique_id(unique.lower())
        self._abort_if_unique_id_configured()

        try:
            await ArgoFamilyClient(self.hass, entry_data).async_get_dashboard()
        except ArgoFamilyError:
            return self.async_abort(reason="cannot_connect")
        except Exception:
            return self.async_abort(reason="unknown")

        return self.async_create_entry(
            title=f"Argo {entry_data['child_name']}",
            data=entry_data,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ArgoFamilyDashboardOptionsFlow(config_entry)


class ArgoFamilyDashboardOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self._config_entry.options.get("scan_interval", 30),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=360)),
                vol.Optional(
                    "attribute_limit",
                    default=self._config_entry.options.get("attribute_limit", 40),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=200)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

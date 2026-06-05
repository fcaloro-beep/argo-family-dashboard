from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .argo_client import ArgoFamilyClient, ArgoFamilyError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ArgoFamilyCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.client = ArgoFamilyClient(hass, dict(entry.data), dict(entry.options))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(
                minutes=int(entry.options.get("scan_interval", 30))
            ),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.async_get_dashboard()
        except ArgoFamilyError as err:
            raise UpdateFailed(str(err)) from err

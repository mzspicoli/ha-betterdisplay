"""DataUpdateCoordinator for BetterDisplay."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BetterDisplayClient, BetterDisplayError
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class BetterDisplayCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    def __init__(self, hass: HomeAssistant, client: BetterDisplayClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            displays = await self.client.list_displays()
            result = {}
            for display in displays:
                tag_id = display["tagID"]
                brightness = await self.client.get_brightness(tag_id)
                result[tag_id] = {**display, "brightness": brightness}
            return result
        except BetterDisplayError as err:
            raise UpdateFailed(str(err)) from err

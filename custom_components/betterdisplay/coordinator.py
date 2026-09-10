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
        # The input source list is static per display, so it's fetched once and kept here
        # rather than re-read on every poll.
        self.input_sources: dict[str, dict[str, str]] = {}
        # Displays that report a hardwareBacklight value but ignore writes to it.
        self.backlight_unsupported: set[str] = set()

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            displays = await self.client.list_displays()
            result = {}
            for display in displays:
                tag_id = display["tagID"]
                if tag_id not in self.input_sources:
                    self.input_sources[tag_id] = await self.client.list_input_sources(tag_id)
                result[tag_id] = {
                    **display,
                    "brightness": await self.client.get_brightness(tag_id),
                    "backlight": await self.client.get_backlight(tag_id),
                    "volume": await self.client.get_volume(tag_id),
                    "mute": await self.client.get_mute(tag_id),
                }
            return result
        except BetterDisplayError as err:
            raise UpdateFailed(str(err)) from err

"""Light platform for BetterDisplay -- exposes display brightness and backlight power."""
from __future__ import annotations

import logging

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import BetterDisplayError
from .const import DOMAIN
from .coordinator import BetterDisplayCoordinator
from .entity import BetterDisplayEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: BetterDisplayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BetterDisplayBrightnessLight(coordinator, tag_id) for tag_id in coordinator.data)


class BetterDisplayBrightnessLight(BetterDisplayEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: BetterDisplayCoordinator, tag_id: str) -> None:
        super().__init__(coordinator, tag_id, "brightness")

    @property
    def _has_backlight_control(self) -> bool:
        return (
            self._display["backlight"] is not None
            and self._tag_id not in self.coordinator.backlight_unsupported
        )

    @property
    def is_on(self) -> bool:
        if self._has_backlight_control:
            return self._display["backlight"]
        return self._display["brightness"] > 0

    @property
    def brightness(self) -> int:
        return round(self._display["brightness"] * 255)

    async def async_turn_on(self, **kwargs) -> None:
        client = self.coordinator.client
        if self._has_backlight_control and not self._display["backlight"]:
            await client.set_backlight(self._tag_id, True)

        if ATTR_BRIGHTNESS in kwargs:
            pct = kwargs[ATTR_BRIGHTNESS] / 255
        elif ATTR_BRIGHTNESS_PCT in kwargs:
            pct = kwargs[ATTR_BRIGHTNESS_PCT] / 100
        elif self._has_backlight_control:
            # Backlight is back on and brightness was never zeroed -- keep the previous level.
            pct = None
        else:
            pct = 1.0

        if pct is not None:
            await client.set_brightness(self._tag_id, pct)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        # Cut the backlight via DDC so the panel actually powers down; dropping brightness
        # to 0 only paints the screen black while the display stays lit.
        client = self.coordinator.client
        if self._has_backlight_control and await self._try_backlight_off():
            await self.coordinator.async_request_refresh()
            return

        await client.set_brightness(self._tag_id, 0.0)
        await self.coordinator.async_request_refresh()

    async def _try_backlight_off(self) -> bool:
        """Turn the backlight off, reporting whether the display actually obeyed.

        BetterDisplay answers 200 with an empty body for parameters a display doesn't
        implement, so a successful write says nothing -- the value has to be read back.
        Displays that ignore it are remembered so later calls skip straight to dimming.
        """
        client = self.coordinator.client
        try:
            await client.set_backlight(self._tag_id, False)
            if not await client.get_backlight(self._tag_id):
                return True
        except BetterDisplayError as err:
            _LOGGER.debug("Backlight control failed for %s: %s", self._tag_id, err)

        _LOGGER.info(
            "Display %s ignores hardwareBacklight; falling back to dimming to 0%%", self._tag_id
        )
        self.coordinator.backlight_unsupported.add(self._tag_id)
        return False

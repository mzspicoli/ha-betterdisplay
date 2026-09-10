"""Number platform for BetterDisplay -- exposes DDC volume."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BetterDisplayCoordinator
from .entity import BetterDisplayEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: BetterDisplayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BetterDisplayVolumeNumber(coordinator, tag_id)
        for tag_id, display in coordinator.data.items()
        if display["volume"] is not None
    )


class BetterDisplayVolumeNumber(BetterDisplayEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: BetterDisplayCoordinator, tag_id: str) -> None:
        super().__init__(coordinator, tag_id, "volume")

    @property
    def native_value(self) -> float:
        return round(self._display["volume"] * 100)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_volume(self._tag_id, value / 100)
        await self.coordinator.async_request_refresh()

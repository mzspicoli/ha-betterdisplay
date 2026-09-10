"""Switch platform for BetterDisplay -- exposes DDC mute."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BetterDisplayCoordinator
from .entity import BetterDisplayEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: BetterDisplayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BetterDisplayMuteSwitch(coordinator, tag_id)
        for tag_id, display in coordinator.data.items()
        if display["mute"] is not None
    )


class BetterDisplayMuteSwitch(BetterDisplayEntity, SwitchEntity):
    def __init__(self, coordinator: BetterDisplayCoordinator, tag_id: str) -> None:
        super().__init__(coordinator, tag_id, "mute")

    @property
    def is_on(self) -> bool:
        return self._display["mute"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._tag_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._tag_id, False)
        await self.coordinator.async_request_refresh()

"""Select platform for BetterDisplay -- exposes DDC input source switching."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BetterDisplayCoordinator
from .entity import BetterDisplayEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: BetterDisplayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BetterDisplayInputSourceSelect(coordinator, tag_id)
        for tag_id in coordinator.data
        if coordinator.input_sources.get(tag_id)
    )


class BetterDisplayInputSourceSelect(BetterDisplayEntity, SelectEntity):
    """Input source picker.

    DDC input source is write-only in practice -- reading VCP 0x60 back fails on most
    Apple Silicon connections -- so the entity reports the last value it sent and is
    `unknown` until something switches the input.
    """

    def __init__(self, coordinator: BetterDisplayCoordinator, tag_id: str) -> None:
        super().__init__(coordinator, tag_id, "input_source")
        self._attr_current_option: str | None = None

    @property
    def _sources(self) -> dict[str, str]:
        return self.coordinator.input_sources[self._tag_id]

    @property
    def options(self) -> list[str]:
        return list(self._sources)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_input_source(self._tag_id, self._sources[option])
        self._attr_current_option = option
        self.async_write_ha_state()

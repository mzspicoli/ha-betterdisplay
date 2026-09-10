"""Shared base entity for BetterDisplay."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BetterDisplayCoordinator


class BetterDisplayEntity(CoordinatorEntity[BetterDisplayCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BetterDisplayCoordinator, tag_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._tag_id = tag_id
        self._attr_translation_key = key
        self._attr_unique_id = f"betterdisplay_{tag_id}_{key}"

    @property
    def _display(self) -> dict:
        return self.coordinator.data[self._tag_id]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._tag_id)},
            name=self._display.get("name", f"Display {self._tag_id}"),
            manufacturer=self._display.get("vendor"),
            model=self._display.get("productName"),
        )

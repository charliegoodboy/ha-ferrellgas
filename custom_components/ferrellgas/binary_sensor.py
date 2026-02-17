"""Binary sensor platform for Ferrellgas."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FerrellgasConfigEntry
from .const import CONF_LOW_PROPANE_THRESHOLD, DEFAULT_LOW_PROPANE_THRESHOLD
from .coordinator import FerrellgasDataUpdateCoordinator
from .entity import FerrellgasTankEntity

LOW_PROPANE_DESCRIPTION = BinarySensorEntityDescription(
    key="low_propane",
    translation_key="low_propane",
    device_class=BinarySensorDeviceClass.PROBLEM,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerrellgasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ferrellgas binary sensors."""
    coordinator = entry.runtime_data

    entities = [
        FerrellgasLowPropaneBinarySensor(coordinator, tank.installed_product_id)
        for tank in coordinator.data.tanks
    ]
    async_add_entities(entities)


class FerrellgasLowPropaneBinarySensor(FerrellgasTankEntity, BinarySensorEntity):
    """Low propane indicator for each tank."""

    entity_description = LOW_PROPANE_DESCRIPTION

    def __init__(
        self,
        coordinator: FerrellgasDataUpdateCoordinator,
        installed_product_id: str,
    ) -> None:
        """Initialize low propane binary sensor."""
        super().__init__(coordinator, installed_product_id)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{installed_product_id}_low_propane"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if tank is below low threshold."""
        tank = self._find_tank()
        if tank is None or tank.est_curr_pct is None:
            return None

        threshold = int(
            self.coordinator.config_entry.options.get(
                CONF_LOW_PROPANE_THRESHOLD,
                DEFAULT_LOW_PROPANE_THRESHOLD,
            )
        )
        return tank.est_curr_pct < threshold

"""Sensor platform for Ferrellgas."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FerrellgasConfigEntry
from .api import FerrellgasAccountData, FerrellgasTankData
from .const import DOMAIN
from .coordinator import FerrellgasDataUpdateCoordinator
from .entity import FerrellgasTankEntity


ValueFunc = Callable[[FerrellgasTankData, FerrellgasAccountData], object]


@dataclass(frozen=True, kw_only=True)
class FerrellgasTankSensorDescription(SensorEntityDescription):
    """Description for Ferrellgas tank sensors."""

    value_fn: ValueFunc


TANK_SENSORS: tuple[FerrellgasTankSensorDescription, ...] = (
    FerrellgasTankSensorDescription(
        key="tank_level",
        translation_key="tank_level",
        icon="mdi:propane-tank",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda tank, _: tank.est_curr_pct,
    ),
    FerrellgasTankSensorDescription(
        key="estimated_gallons",
        translation_key="estimated_gallons",
        icon="mdi:propane-tank",
        native_unit_of_measurement="gal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda tank, _: (
            round((tank.est_curr_pct / 100.0) * tank.full_capacity, 1)
            if tank.est_curr_pct is not None and tank.full_capacity is not None
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="tank_capacity",
        translation_key="tank_capacity",
        native_unit_of_measurement="gal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.full_capacity,
    ),
    FerrellgasTankSensorDescription(
        key="fill_capacity",
        translation_key="fill_capacity",
        native_unit_of_measurement="gal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.fill_capacity,
    ),
    FerrellgasTankSensorDescription(
        key="last_reading_date",
        translation_key="last_reading_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.estimated_percentage_date,
    ),
)

ACCOUNT_BALANCE_DESCRIPTION = SensorEntityDescription(
    key="account_balance",
    translation_key="account_balance",
    device_class=SensorDeviceClass.MONETARY,
    native_unit_of_measurement="USD",
    state_class=SensorStateClass.MEASUREMENT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerrellgasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ferrellgas sensors."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        FerrellgasAccountBalanceSensor(coordinator),
    ]

    for tank in coordinator.data.tanks:
        for description in TANK_SENSORS:
            entities.append(
                FerrellgasTankSensor(coordinator, tank.installed_product_id, description)
            )

    async_add_entities(entities)


class FerrellgasTankSensor(FerrellgasTankEntity, SensorEntity):
    """Representation of a Ferrellgas per-tank sensor."""

    entity_description: FerrellgasTankSensorDescription

    def __init__(
        self,
        coordinator: FerrellgasDataUpdateCoordinator,
        installed_product_id: str,
        description: FerrellgasTankSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, installed_product_id)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{installed_product_id}_{description.key}"
        )

    @property
    def native_value(self) -> object:
        """Return the sensor value."""
        tank = self._find_tank()
        if tank is None:
            return None
        return self.entity_description.value_fn(tank, self.coordinator.data)


class FerrellgasAccountBalanceSensor(
    CoordinatorEntity[FerrellgasDataUpdateCoordinator], SensorEntity
):
    """Representation of the Ferrellgas account balance sensor."""

    _attr_has_entity_name = True
    entity_description = ACCOUNT_BALANCE_DESCRIPTION

    def __init__(self, coordinator: FerrellgasDataUpdateCoordinator) -> None:
        """Initialize account balance sensor."""
        super().__init__(coordinator)
        account_id = coordinator.data.account_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"account_{account_id}")},
            name=f"Ferrellgas Account {account_id}",
            manufacturer="Ferrellgas",
            model="Customer Account",
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_account_balance"

    @property
    def native_value(self) -> float | None:
        """Return account balance."""
        return self.coordinator.data.balance

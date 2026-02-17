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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FerrellgasConfigEntry
from .api import FerrellgasAccountData, FerrellgasTankData
from .coordinator import FerrellgasDataUpdateCoordinator
from .entity import FerrellgasTankEntity


ValueFunc = Callable[[FerrellgasTankData, FerrellgasAccountData], object]


@dataclass(frozen=True, kw_only=True)
class FerrellgasTankSensorDescription(SensorEntityDescription):
    """Description for Ferrellgas tank sensors."""

    value_fn: ValueFunc


TANK_SENSORS: tuple[FerrellgasTankSensorDescription, ...] = (
    # --- Primary tank sensors ---
    FerrellgasTankSensorDescription(
        key="tank_level",
        name="Tank level",
        icon="mdi:propane-tank",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda tank, _: tank.est_curr_pct,
    ),
    FerrellgasTankSensorDescription(
        key="estimated_gallons",
        name="Estimated gallons",
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
        key="estimated_value",
        name="Propane value",
        icon="mdi:currency-usd",
        native_unit_of_measurement="USD",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda tank, _: (
            round(
                (tank.est_curr_pct / 100.0)
                * tank.full_capacity
                * tank.last_delivery.propane_price_per_gallon,
                2,
            )
            if (
                tank.est_curr_pct is not None
                and tank.full_capacity is not None
                and tank.last_delivery is not None
                and tank.last_delivery.propane_price_per_gallon is not None
            )
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="gallons_used_since_fill",
        name="Gallons used since fill",
        icon="mdi:fire",
        native_unit_of_measurement="gal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda tank, _: (
            round(
                tank.fill_capacity - (tank.est_curr_pct / 100.0) * tank.full_capacity,
                1,
            )
            if (
                tank.fill_capacity is not None
                and tank.est_curr_pct is not None
                and tank.full_capacity is not None
                and tank.fill_capacity >= (tank.est_curr_pct / 100.0) * tank.full_capacity
            )
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="estimated_usage_cost",
        name="Usage cost since fill",
        icon="mdi:cash-minus",
        native_unit_of_measurement="USD",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda tank, _: (
            round(
                (
                    tank.fill_capacity
                    - (tank.est_curr_pct / 100.0) * tank.full_capacity
                )
                * tank.last_delivery.propane_price_per_gallon,
                2,
            )
            if (
                tank.fill_capacity is not None
                and tank.est_curr_pct is not None
                and tank.full_capacity is not None
                and tank.last_delivery is not None
                and tank.last_delivery.propane_price_per_gallon is not None
                and tank.fill_capacity >= (tank.est_curr_pct / 100.0) * tank.full_capacity
            )
            else None
        ),
    ),
    # --- Delivery sensors ---
    FerrellgasTankSensorDescription(
        key="last_delivery_date",
        name="Last delivery",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda tank, _: (
            tank.last_delivery.complete_date
            if tank.last_delivery is not None
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="last_price_per_gallon",
        name="Price per gallon",
        icon="mdi:tag-text",
        native_unit_of_measurement="$/gal",
        suggested_display_precision=4,
        value_fn=lambda tank, _: (
            tank.last_delivery.propane_price_per_gallon
            if tank.last_delivery is not None
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="last_delivery_total",
        name="Last delivery cost",
        icon="mdi:receipt-text",
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=lambda tank, _: (
            tank.last_delivery.grand_total
            if tank.last_delivery is not None
            else None
        ),
    ),
    # --- Diagnostic sensors ---
    FerrellgasTankSensorDescription(
        key="last_delivery_gallons",
        name="Last delivery gallons",
        icon="mdi:propane-tank-outline",
        native_unit_of_measurement="gal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: (
            tank.last_delivery.propane_gallons
            if tank.last_delivery is not None
            else None
        ),
    ),
    FerrellgasTankSensorDescription(
        key="tank_capacity",
        name="Tank capacity",
        native_unit_of_measurement="gal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.full_capacity,
    ),
    FerrellgasTankSensorDescription(
        key="fill_capacity",
        name="Fill capacity",
        native_unit_of_measurement="gal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.fill_capacity,
    ),
    FerrellgasTankSensorDescription(
        key="last_reading_date",
        name="Last reading",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tank, _: tank.estimated_percentage_date,
    ),
    FerrellgasTankSensorDescription(
        key="account_balance",
        name="Account balance",
        icon="mdi:credit-card-outline",
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _, account: account.balance,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerrellgasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ferrellgas sensors."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []

    for tank in coordinator.data.tanks:
        for description in TANK_SENSORS:
            entities.append(
                FerrellgasTankSensor(coordinator, tank.installed_product_id, description)
            )

    async_add_entities(entities)


class FerrellgasTankSensor(FerrellgasTankEntity, SensorEntity):
    """Representation of a Ferrellgas sensor."""

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

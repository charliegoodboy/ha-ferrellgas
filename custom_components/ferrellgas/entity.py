"""Base entity for Ferrellgas."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FerrellgasTankData
from .const import DOMAIN
from .coordinator import FerrellgasDataUpdateCoordinator


class FerrellgasTankEntity(CoordinatorEntity[FerrellgasDataUpdateCoordinator]):
    """Base entity for a Ferrellgas tank."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FerrellgasDataUpdateCoordinator,
        installed_product_id: str,
    ) -> None:
        """Initialize the tank entity."""
        super().__init__(coordinator)
        self._installed_product_id = installed_product_id

        tank = self._find_tank()
        device_name = (
            f"{tank.site_name} - {tank.product_description}"
            if tank is not None
            else installed_product_id
        )
        device_model = tank.product_description if tank is not None else "Ferrellgas Tank"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, installed_product_id)},
            name=device_name,
            manufacturer="Ferrellgas",
            model=device_model,
        )

    def _find_tank(self) -> FerrellgasTankData | None:
        """Find tank by installed product ID."""
        for tank in self.coordinator.data.tanks:
            if tank.installed_product_id == self._installed_product_id:
                return tank
        return None

    @property
    def available(self) -> bool:
        """Return whether this entity is available."""
        return super().available and self._find_tank() is not None

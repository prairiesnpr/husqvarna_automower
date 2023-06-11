"""Platform for Husqvarna Automower basic entity."""

import logging
from datetime import datetime

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from . import AutomowerDataUpdateCoordinator
from .const import DOMAIN, HUSQVARNA_URL

_LOGGER = logging.getLogger(__name__)

class AutomowerStateHelper:
    """State helper"""
    def __init__(self, mower_attributes: dict) -> None:
        self.mower_attributes = mower_attributes
    @property
    def metadata(self) -> dict:
        return self.mower_attributes.get("metadata", {})
    @property
    def connected(self) -> bool:
        return self.metadata.get("connected", False)
    @property
    def system(self) -> dict:
        return self.mower_attributes.get("system", {})
    @property
    def name(self) -> str:
        return self.system.get("name")
    @property
    def model(self) -> str:
        return self.system.get("model")
    @property
    def mower(self) -> dict:
        return self.mower_attributes.get("mower", {})
    @property
    def activity(self) -> str:
        return self.mower.get("activity")
    @property
    def positions(self) -> list:
        return self.mower_attributes.get("positions", [])
    @property
    def calendar(self) -> dict:
        return self.mower_attributes.get("calendar", {})
    @property
    def calendar_tasks(self) -> list:
        return self.calendar.get("tasks", [])
    @property
    def cutting_height(self) -> int:
        return self.mower_attributes.get("cuttingHeight")
    @property
    def headlight(self) -> dict:
        return self.mower_attributes.get("headlight", {})
    @property
    def headlight_mode(self) -> str:
        return self.headlight.get("mode")
    @property
    def state(self) -> str:
        return self.mower.get("state")
    @property
    def error_code(self) -> str:
        return self.mower.get("errorCode")
    @property
    def mower_mode(self) -> str:
        return self.mower.get("mode")
    @property
    def battery(self) -> dict:
        return self.mower_attributes.get("battery", {})
    @property
    def battery_percent(self) -> int:
        return self.battery.get("batteryPercent")
    @property
    def planner(self) -> dict:
        return self.mower_attributes.get("planner", {})
    @property
    def restricted_reason(self) -> str:
        return self.planner.get("restrictedReason")
    @property
    def planner_override(self) -> dict:
        return self.planner.get("override", {})
    @property
    def planner_override_action(self) -> str:
        return self.planner_override.get("action")
    @property
    def planner_next_start(self) -> int:
        return self.planner.get("nextStartTimestamp", 0)
    @property
    def statistics(self) -> dict:
        return self.mower.get("statistics", {})















class AutomowerEntity(CoordinatorEntity[AutomowerDataUpdateCoordinator]):
    """Defining the Automower Basic Entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, idx) -> None:
        """Initialize AutomowerEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.mower = coordinator.session.data["data"][self.idx]
        mower_attributes = self.get_mower_attributes()
        self.mower_id = self.mower["id"]
        self.mower_name = mower_attributes.name
        self._model = mower_attributes.model

        self._available = self.get_mower_attributes().connected

    def get_mower_attributes(self) -> AutomowerStateHelper:
        """Get the mower attributes of the current mower."""
        return AutomowerStateHelper(self.coordinator.session.data["data"][self.idx]["attributes"])

    def datetime_object(self, timestamp) -> datetime:
        """Convert the mower local timestamp to a UTC datetime object."""
        if timestamp != 0:
            naive = datetime.utcfromtimestamp(timestamp / 1000)
            local = dt_util.as_local(naive)
        if timestamp == 0:
            local = None
        return local

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to Home Assistant."""
        await super().async_added_to_hass()
        self.coordinator.session.register_data_callback(
            lambda _: self.async_write_ha_state(), schedule_immediately=True
        )

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity is being removed from Home Assistant."""
        await super().async_will_remove_from_hass()
        self.coordinator.session.unregister_data_callback(
            lambda _: self.async_write_ha_state()
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Define the DeviceInfo for the mower."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.mower_id)},
            name=self.mower_name,
            manufacturer="Husqvarna",
            model=self._model,
            configuration_url=HUSQVARNA_URL,
            suggested_area="Garden",
        )

    @property
    def _is_home(self):
        """Return True if the mower is located at the charging station."""
        if self.get_mower_attributes().activity in [
            "PARKED_IN_CS",
            "CHARGING",
        ]:
            return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return True if the device is available."""
        return False

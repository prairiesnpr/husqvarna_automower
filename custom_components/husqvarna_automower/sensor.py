"""Creates a sensor entity for the mower."""
from collections.abc import Callable
from dataclasses import dataclass
import logging
import json

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, TIME_SECONDS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from shapely.geometry import Point, Polygon

from .const import (
    DOMAIN,
    ERRORCODES,
    CONF_ZONES,
    HOME_LOCATION,
    ZONE_COORD,
    ZONE_ID,
    ZONE_NAME,
)
from .const import DOMAIN, ERRORCODES, NO_SUPPORT_FOR_CHANGING_CUTTING_HEIGHT
from .entity import AutomowerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class AutomowerSensorRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[AutomowerEntity], int]


@dataclass
class AutomowerSensorEntityDescription(
    SensorEntityDescription, AutomowerSensorRequiredKeysMixin
):
    """Describes a sensor sensor entity."""


def get_problem(mower_attributes) -> dict:
    """Get the mower attributes of the current mower."""
    if mower_attributes["mower"]["state"] == "RESTRICTED":
        if mower_attributes["planner"]["restrictedReason"] == "NOT_APPLICABLE":
            return None
        return mower_attributes["planner"]["restrictedReason"]
    if mower_attributes["mower"]["state"] in [
        "ERROR",
        "FATAL_ERROR",
        "ERROR_AT_POWER_UP",
    ]:
        return ERRORCODES.get(mower_attributes["mower"]["errorCode"])
    if mower_attributes["mower"]["state"] in [
        "UNKNOWN",
        "STOPPED",
        "OFF",
    ]:
        return mower_attributes["mower"]["state"]
    if mower_attributes["mower"]["activity"] in [
        "STOPPED_IN_GARDEN",
        "UNKNOWN",
        "NOT_APPLICABLE",
    ]:
        return mower_attributes["mower"]["activity"]
    return None


SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    AutomowerSensorEntityDescription(
        key="cuttingBladeUsageTime",
        name="Cutting blade usage time",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=TIME_SECONDS,
        value_fn=lambda data: data["statistics"]["cuttingBladeUsageTime"],
    ),
    AutomowerSensorEntityDescription(
        key="totalChargingTime",
        name="Total charging time",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=TIME_SECONDS,
        value_fn=lambda data: data["statistics"]["totalChargingTime"],
    ),
    AutomowerSensorEntityDescription(
        key="totalCuttingTime",
        name="Total cutting time",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=TIME_SECONDS,
        value_fn=lambda data: data["statistics"]["totalCuttingTime"],
    ),
    AutomowerSensorEntityDescription(
        key="totalRunningTime",
        name="Total running time",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=TIME_SECONDS,
        value_fn=lambda data: data["statistics"]["totalRunningTime"],
    ),
    AutomowerSensorEntityDescription(
        key="totalSearchingTime",
        name="Total searching time",
        icon="mdi:clock-outline",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=TIME_SECONDS,
        value_fn=lambda data: data["statistics"]["totalSearchingTime"],
    ),
    AutomowerSensorEntityDescription(
        key="numberOfChargingCycles",
        name="Number of charging cycles",
        icon="mdi:battery-sync-outline",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["statistics"]["numberOfChargingCycles"],
    ),
    AutomowerSensorEntityDescription(
        key="numberOfCollisions",
        name="Number of collisions",
        icon="mdi:counter",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["statistics"]["numberOfCollisions"],
    ),
    AutomowerSensorEntityDescription(
        key="totalSearchingTime_percentage",
        name="Searching time percent",
        icon="mdi:percent",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: round(
            data["statistics"]["totalSearchingTime"]
            / data["statistics"]["totalRunningTime"]
            * 100,
            2,
        ),
    ),
    AutomowerSensorEntityDescription(
        key="totalCuttingTime_percentage",
        name="Cutting time percent",
        icon="mdi:percent",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: round(
            data["statistics"]["totalCuttingTime"]
            / data["statistics"]["totalRunningTime"]
            * 100,
            2,
        ),
    ),
    AutomowerSensorEntityDescription(
        key="battery_level",
        name="Battery level",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data["battery"]["batteryPercent"],
    ),
    AutomowerSensorEntityDescription(
        key="next_start",
        name="Next start",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: AutomowerEntity.datetime_object(
            data, data["planner"]["nextStartTimestamp"]
        ),
    ),
    AutomowerSensorEntityDescription(
        key="mode",
        name="Mode",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data["mower"]["mode"],
    ),
    AutomowerSensorEntityDescription(
        key="problem_sensor",
        name="Problem Sensor",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: get_problem(data),
    ),
    AutomowerSensorEntityDescription(
        key="cuttingHeight",
        name="Cutting height",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:grass",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["cuttingHeight"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up select platform."""
    session = hass.data[DOMAIN][entry.entry_id]
    
    entity_list = []
    for idx, ent in enumerate(session.data["data"]):
        entity_list.append(AutomowerZoneSensor(session, idx, entry))
        for description in SENSOR_TYPES:
            try:
                description.value_fn(session.data["data"][idx]["attributes"])
                if description.key == "cuttingHeight":
                    if any(
                        ele
                        in session.data["data"][idx]["attributes"]["system"]["model"]
                        for ele in NO_SUPPORT_FOR_CHANGING_CUTTING_HEIGHT
                    ):
                        entity_list.append(AutomowerSensor(session, idx, description))
                if description.key != "cuttingHeight":
                    entity_list.append(AutomowerSensor(session, idx, description))
            except KeyError:
                pass

    async_add_entities(entity_list)


class AutomowerZoneSensor(SensorEntity, AutomowerEntity):
    """Define the AutomowerZoneSensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, session, idx, entry):
        """Initialize the zone object."""
        super().__init__(session, idx)
        self._attr_name = f"{self.mower_name} Zone Sensor"
        self._attr_unique_id = f"{self.mower_id}_zone_sensor"
        self.entry = entry
        self.zones = self._load_zones()
        self.home_location = self.entry.options.get(HOME_LOCATION, None)
        self.zone = {ZONE_NAME: "Unknown"}
        self.zone_id = "unknown"

    def _load_zones(self):
        """Load zones from a config entry."""
        return json.loads(self.entry.options.get(CONF_ZONES, "{}"))

    def _find_current_zone(self):
        """Find current zone."""
        if self._is_home and self.home_location:
            self.zone = {ZONE_NAME: "Home"}
            self.zone_id = "home"
            return

        lat = AutomowerEntity.get_mower_attributes(self)["positions"][0]["latitude"]
        lon = AutomowerEntity.get_mower_attributes(self)["positions"][0]["longitude"]
        location = Point(lat, lon)
        for zone_id, zone in self.zones.items():
            zone_poly = Polygon(zone.get(ZONE_COORD))
            if zone_poly.contains(location):
                self.zone = zone
                self.zone_id = zone_id
                return
        self.zone = {ZONE_NAME: "Unknown"}
        self.zone_id = "unknown"

    @property
    def native_value(self) -> str:
        """Return a the current zone of the mower."""
        self._find_current_zone()
        return self.zone.get(ZONE_NAME)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the specific state attributes of this mower."""
        return {ZONE_ID: self.zone_id}
   

class AutomowerSensor(SensorEntity, AutomowerEntity):
    """Defining the Automower Sensors with AutomowerSensorEntityDescription."""

    def __init__(self, session, idx, description: AutomowerSensorEntityDescription):
        """Set up AutomowerSensors."""
        super().__init__(session, idx)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{self.mower_id}_{description.key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        mower_attributes = AutomowerEntity.get_mower_attributes(self)
        return self.entity_description.value_fn(mower_attributes)

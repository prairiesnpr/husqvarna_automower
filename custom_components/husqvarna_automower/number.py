"""Platform for Husqvarna Automower device tracker integration."""
import logging
import json

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed
import aioautomower
from homeassistant.const import CONF_TOKEN

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices) -> None:
    """Setup sensor platform."""

    session = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Model %s", session.data["data"])
    async_add_devices(
        AutomowerNumber(session, idx) for idx in enumerate(session.data["data"])
    )


class AutomowerNumber(NumberEntity):
    """Defining the Device Tracker Entity."""

    def __init__(self, session, idx) -> None:
        self.session = session
        self.idx = idx
        self.mower = self.session.data["data"][self.idx]

        mower_attributes = self.__get_mower_attributes()
        self.mower_id = self.mower["id"]
        self.mower_name = mower_attributes["system"]["name"]
        self.model = mower_attributes["system"]["model"]

        self.session.register_cb(
            lambda _: self.async_write_ha_state(), schedule_immediately=True
        )

        self._attr_current_option = mower_attributes["settings"]["headlight"]["mode"]

    def __get_mower_attributes(self) -> dict:
        return self.session.data["data"][self.idx]["attributes"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.mower_id)})

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.mower_name}_cuttingheight"

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this entity."""
        return f"{self.mower_id}_cuttingheight"

    @property
    def min_value(self) -> float:
        """Return the minimum value."""
        return 1

    @property
    def max_value(self) -> float:
        """Return the maximum value."""
        return 9

    @property
    def value(self) -> int:
        """Return the entity value."""
        mower_attributes = self.__get_mower_attributes()
        return mower_attributes["settings"]["cuttingHeight"]

    async def async_set_value(self, value: float) -> None:
        """Change the selected option."""
        mower_attributes = self.__get_mower_attributes()
        command_type = "settings"
        string = {
            "data": {
                "type": "settings",
                "attributes": {
                    "cuttingHeight": value,
                    "headlight": {
                        "mode": mower_attributes["settings"]["headlight"]["mode"]
                    },
                },
            }
        }
        payload = json.dumps(string)
        try:
            await self.session.action(self.mower_id, payload, command_type)
        except Exception as exception:
            raise UpdateFailed(exception) from exception

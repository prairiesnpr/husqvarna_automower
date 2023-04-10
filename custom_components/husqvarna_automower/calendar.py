"""Platform for Husqvarna Automower calendar integration."""
from datetime import datetime
import logging

from geopy.geocoders import Nominatim

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
    CalendarEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util
import voluptuous as vol
from .const import DOMAIN, WEEKDAYS, WEEKDAYS_TO_RFC5545
from .entity import AutomowerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up calendar platform."""
    _LOGGER.debug("entry: %s", entry)
    session = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AutomowerCalendar(session, idx) for idx, ent in enumerate(session.data["data"])
    )


class AutomowerCalendar(CalendarEntity, AutomowerEntity):
    """Representation of the Automower Calendar element."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
    )

    def __init__(self, session, idx):
        """Initialize AutomowerCalendar."""
        super().__init__(session, idx)
        self._event = None
        self._next_event = None
        self.loc = None
        self.geolocator = Nominatim(user_agent=self.mower_id)
        self._attr_unique_id = f"{self.mower_id}_calendar"

    async def async_get_events_data(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        mower_attributes = AutomowerEntity.get_mower_attributes(self)
        lat = mower_attributes["positions"][0]["latitude"]
        long = mower_attributes["positions"][0]["longitude"]
        position = f"{lat}, {long}"
        result = await hass.async_add_executor_job(self.geolocator.reverse, position)
        try:
            self.loc = f"{result.raw['address']['road']} {result.raw['address']['house_number']}, {result.raw['address']['town']}"
        except Exception:
            self.loc = None

        even_list, next_event = self.get_next_event()
        return even_list

    def get_next_event(self):
        """Get the current or next event."""
        self._next_event = CalendarEvent(
            summary="",
            start=dt_util.start_of_local_day() + dt_util.dt.timedelta(days=7),
            end=dt_util.start_of_local_day() + dt_util.dt.timedelta(days=7, hours=2),
            location="",
            description="Good time to mow",
        )
        event_list = []
        mower_attributes = AutomowerEntity.get_mower_attributes(self)
        for task, tasks in enumerate(mower_attributes["calendar"]["tasks"]):
            calendar = mower_attributes["calendar"]["tasks"][task]
            start_of_day = dt_util.start_of_local_day()
            start_mowing = start_of_day + dt_util.dt.timedelta(
                minutes=calendar["start"]
            )
            end_mowing = start_of_day + dt_util.dt.timedelta(
                minutes=calendar["start"] + calendar["duration"]
            )

            for days in range(7):
                today = (start_of_day + dt_util.dt.timedelta(days=days)).weekday()
                today_as_string = WEEKDAYS[today]
                if calendar[today_as_string] is True:
                    today_rfc = WEEKDAYS_TO_RFC5545[today_as_string]
                    self._event = CalendarEvent(
                        summary=f"{self.mower_name} Mowing schedule {task + 1}",
                        start=start_mowing + dt_util.dt.timedelta(days=days),
                        end=end_mowing + dt_util.dt.timedelta(days=days),
                        location=self.loc,
                        rrule=f"FREQ=WEEKLY;BYDAY={today_rfc}",
                        uid=f"{self.mower_name}-{task + 1}",
                        description="Nice day to mow",
                    )
                    if self._event.start < self._next_event.start:
                        self._next_event = self._event

                    event_list.append(self._event)

        return event_list, self._next_event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return await self.async_get_events_data(hass, start_date, end_date)

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        even_list, next_event = self.get_next_event()
        return next_event

    async def async_update_event(
        self,
        uid: str,
        event: dict[str],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Update an existing event on the calendar."""
        _LOGGER.debug("input: %s", event)
        try:
            _LOGGER.debug("rrule: %s", event["rrule"])
            event["rrule"]
        except KeyError as exc:
            raise vol.Invalid("Only reccuring events are allowed") from exc
        if not "WEEKLY" in event["rrule"]:
            raise vol.Invalid("Please select weekly")
        if not "BYDAY" in event["rrule"]:
            raise vol.Invalid("Please select day(s)")
        days = event["rrule"].lstrip("FREQ=WEKLY;BDA=")
        day_list = days.split(",")
        _LOGGER.debug("daylist: %s", day_list)
        _LOGGER.debug("dtstart: %s", event["dtstart"].hour)
        for daily_task in WEEKDAYS:
            if daily_task:
                start_time = daily_task["from"].split(":")
                start_time_minutes = int(start_time[0]) * 60 + int(
                    start_time[1]
                )
                end_time = daily_task["to"].split(":")
                end_time_minutes = int(end_time[0]) * 60 + int(end_time[1])
                duration = end_time_minutes - start_time_minutes
                addition = {}
                relevant_day = False
                addition = {
                    "start": start_time_minutes,
                    "duration": duration,
                }
                for relevant_day in WEEKDAYS:
                    if day == relevant_day:
                        addition[relevant_day] = True
                    else:
                        addition[relevant_day] = False
                task_list.append(addition)
        await self.async_update_ha_state(force_refresh=True)

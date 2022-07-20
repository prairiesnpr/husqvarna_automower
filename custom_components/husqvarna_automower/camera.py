"""Platform for Husqvarna Automower camera integration."""

import io
import logging
import math
import json
from typing import Optional
from datetime import datetime

from PIL import Image, ImageDraw
import numpy as np

from homeassistant.components.camera import CameraEntityFeature, Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENABLE_CAMERA,
    GPS_BOTTOM_RIGHT,
    GPS_TOP_LEFT,
    MAP_IMG_PATH,
    MOWER_IMG_PATH,
    MAP_PATH_COLOR,
    HOME_LOCATION,
    CONF_ZONES,
    ZONE_COORD,
    ZONE_COLOR,
    ZONE_DISPLAY,
)
from .entity import AutomowerEntity
from .vacuum import HusqvarnaAutomowerStateMixin

GpsPoint = tuple[float, float]
ImgPoint = tuple[int, int]
ImgDimensions = tuple[int, int]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up select platform."""
    session = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AutomowerCamera(session, idx, entry)
        for idx, ent in enumerate(session.data["data"])
    )


class AutomowerCamera(HusqvarnaAutomowerStateMixin, Camera, AutomowerEntity):
    """Representation of the AutomowerCamera element."""

    _attr_entity_registry_enabled_default = False
    _attr_frame_interval: float = 300
    _attr_name = "Map"

    def __init__(self, session, idx, entry):
        """Initialize AutomowerCamera."""
        Camera.__init__(self)
        AutomowerEntity.__init__(self, session, idx)

        self.entry = entry
        self._position_history = []
        self._attr_unique_id = f"{self.mower_id}_camera"
        self.home_location = self.entry.options.get(HOME_LOCATION, None)
        self._image = Image.new(mode="RGB", size=(200, 200))
        self._image_bytes = None
        self._image_to_bytes()
        self._map_image = None
        self._overlay_image = None
        self._path_color = self.entry.options.get(MAP_PATH_COLOR, [255, 0, 0])
        self._last_update = None
        self._update_frequency = 0
        self._avg_update_frequency = 0

        self.session = session

        if self.entry.options.get(ENABLE_CAMERA, False):
            self.top_left_coord = self.entry.options.get(GPS_TOP_LEFT)
            self.bottom_right_coord = self.entry.options.get(GPS_BOTTOM_RIGHT)
            self._load_map_image()
            self._load_mower_image()
            self._overlay_zones()
            self.session.register_data_callback(
                lambda data: self._generate_image(data), schedule_immediately=True
            )
        else:
            self._attr_entity_registry_enabled_default = True
            r_earth = 6378000  # meters
            offset = 100  # meters
            pi = 3.14
            lat = AutomowerEntity.get_mower_attributes(self)["positions"][0]["latitude"]
            lon = AutomowerEntity.get_mower_attributes(self)["positions"][0][
                "longitude"
            ]
            top_left_lat = lat - (offset / r_earth) * (180 / pi)
            top_left_lon = lon - (offset / r_earth) * (180 / pi) / math.cos(
                lat * pi / 180
            )
            bottom_right_lat = lat + (offset / r_earth) * (180 / pi)
            bottom_right_lon = lon + (offset / r_earth) * (180 / pi) / math.cos(
                lat * pi / 180
            )
            self.top_left_coord = (top_left_lat, top_left_lon)
            self.bottom_right_coord = (bottom_right_lat, bottom_right_lon)

    def model(self) -> str:
        """Return the mower model."""
        return self.model

    async def async_camera_image(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> Optional[bytes]:
        """Return the caerma image."""
        return self._image_bytes

    def _load_map_image(self):
        """Load the map image."""
        map_image_path = self.entry.options.get(MAP_IMG_PATH)
        self._map_image = Image.open(map_image_path, "r")

    def _load_mower_image(self):
        """Load the mower overlay image."""
        overlay_path = self.entry.options.get(MOWER_IMG_PATH)
        self._overlay_image = Image.open(overlay_path, "r")
        mower_img_w = 64
        mower_wpercent = mower_img_w / float(self._overlay_image.size[0])
        hsize = int((float(self._overlay_image.size[1]) * float(mower_wpercent)))
        self._overlay_image = self._overlay_image.resize(
            (mower_img_w, hsize), Image.ANTIALIAS
        )

    def _overlay_zones(self) -> None:
        """Draw zone overlays."""
        zones = json.loads(self.entry.options.get(CONF_ZONES, "{}"))

        for zone_id, zone in zones.items():
            if zone.get(ZONE_DISPLAY, False):
                zone_poly = [
                    self._scale_to_img(
                        point, (self._map_image.size[0], self._map_image.size[1])
                    )
                    for point in zone.get(ZONE_COORD)
                ]
                poly_img = Image.new(
                    "RGBA", (self._map_image.size[0], self._map_image.size[1])
                )
                pdraw = ImageDraw.Draw(poly_img)

                zone_color = zone.get(ZONE_COLOR, [255, 255, 255])

                pdraw.polygon(
                    zone_poly,
                    fill=tuple(zone_color + [25]),
                    outline=tuple(zone_color + [255]),
                )
                self._map_image.paste(poly_img, mask=poly_img)

    def _image_to_bytes(self) -> None:
        """Convert image to byte array."""
        img_byte_arr = io.BytesIO()
        self._image.save(img_byte_arr, format="PNG")
        self._image_bytes = img_byte_arr.getvalue()

    def turn_on(self) -> None:
        """Turn the camera on."""
        self.session.register_data_callback(
            lambda data: self._generate_image(data), schedule_immediately=True
        )

    def turn_off(self) -> None:
        """Turn the camera off."""
        self.session.unregister_data_callback(lambda data: self._generate_image(data))

    @property
    def supported_features(self) -> int:
        """Show supported features."""
        return CameraEntityFeature.ON_OFF

    @property
    def extra_state_attributes(self) -> dict:
        """Return the extra state attributes of this map camera."""
        return {"update_frequency_seconds": self._update_frequency,
                "average_update_freq_sec": self._avg_update_frequency,
                "last_update": self._last_update}

    def _generate_image(self, data: dict) -> None:
        """Generate the image."""
        if self._last_update is not None:
            update_frequency = (datetime.now() - self._last_update).seconds
            if update_frequency > 0:
                self._update_frequency = update_frequency
                self._avg_update_frequency = (self._avg_update_frequency + self._update_frequency)/2
            else:
                return

        self._last_update = datetime.now()

        position_history = AutomowerEntity.get_mower_attributes(self)["positions"]
        map_image = self._map_image.copy()

        if self._is_home and self.home_location:
            location = self.home_location
        else:
            location = (
                position_history[0]["latitude"],
                position_history[0]["longitude"],
            )
        if len(position_history) == 1:
            self._position_history += position_history
            position_history = self._position_history
        else:
            self._position_history = position_history

        x1, y1 = self._scale_to_img(
            location, (map_image.size[0], map_image.size[1])
        )
        img_draw = ImageDraw.Draw(map_image)

        for i in range(len(position_history) - 1, 0, -1):
            point_1 = (
                position_history[i]["latitude"],
                position_history[i]["longitude"],
            )
            scaled_loc_1 = self._scale_to_img(
                point_1, (map_image.size[0], map_image.size[1])
            )
            point_2 = (
                position_history[i - 1]["latitude"],
                position_history[i - 1]["longitude"],
            )
            scaled_loc_2 = self._scale_to_img(
                point_2, (map_image.size[0], map_image.size[1])
            )
            plot_points = self._find_points_on_line(scaled_loc_1, scaled_loc_2)
            for p in range(0, len(plot_points) - 1, 2):
                img_draw.line(
                    (plot_points[p], plot_points[p + 1]),
                    fill=tuple(self._path_color + [255]),
                    width=2,
                )

        img_w, img_h = self._overlay_image.size

        map_image.paste(
            self._overlay_image, (x1 - img_w // 2, y1 - img_h), self._overlay_image
        )
        self._image = map_image
        self._image_to_bytes()

    def _find_points_on_line(
        self, point_1: ImgPoint, point_2: ImgPoint
    ) -> list[ImgPoint]:
        """Find points on a line."""
        dash_length = 10
        line_length = math.sqrt(
            (point_2[0] - point_1[0]) ** 2 + (point_2[1] - point_1[1]) ** 2
        )
        dashes = int(line_length // dash_length)

        points = []
        points.append(point_1)
        for i in range(dashes):
            points.append(self._get_point_on_vector(points[-1], point_2, dash_length))

        points.append(point_2)

        return points

    def _get_point_on_vector(
        self, initial_pt: ImgPoint, terminal_pt: ImgPoint, distance: int
    ) -> ImgPoint:
        """Get points on a vector."""
        v = np.array(initial_pt, dtype=float)
        u = np.array(terminal_pt, dtype=float)
        n = v - u
        n /= np.linalg.norm(n, 2)
        point = v - distance * n

        return tuple(point)

    def _scale_to_img(self, lat_lon: GpsPoint, h_w: ImgDimensions) -> ImgPoint:
        """Convert from latitude and longitude to the image pixels."""
        old = (self.bottom_right_coord[0], self.top_left_coord[0])
        new = (0, h_w[1])
        y = ((lat_lon[0] - old[0]) * (new[1] - new[0]) / (old[1] - old[0])) + new[0]
        old = (self.top_left_coord[1], self.bottom_right_coord[1])
        new = (0, h_w[0])
        x = ((lat_lon[1] - old[0]) * (new[1] - new[0]) / (old[1] - old[0])) + new[0]
        return int(x), h_w[1] - int(y)

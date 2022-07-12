from shapely.geometry import Point
from .const import LAT_LON_BOUNDS


class LatLon:
    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon

    @property
    def point(self) -> Point:
        return Point(self.lat, self.lon)

    def is_valid(self) -> bool:
        return LAT_LON_BOUNDS.intersects(self.point)


class ValidatePointString:
    def __init__(self, point_string: str) -> None:
        self.point_str = point_string
        self.point_list = self.point_str.split(",")
        self.error = ""
        self.valid = False
        self.coord = None

        if len(self.point_list) != 2:
            self.error = "invalid_str"
            return

        try:
            self.coord = LatLon(float(self.point_list[0]), float(self.point_list[1]))
            if not self.coord.is_valid():
                self.error = "not_wgs84"
                return
        except ValueError:
            self.error = "cant_parse"
            return

        self.valid = True

    def is_valid(self) -> tuple[bool, str]:
        return (self.valid, self.error)

    @property
    def point(self) -> Point:
        return self.coord.point

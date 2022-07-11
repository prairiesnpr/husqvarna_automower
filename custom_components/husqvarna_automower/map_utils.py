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

    def to_tuple(self) -> tuple[float, float]:
        return (self.lat, self.lon)


class ValidatePointString:
    def __init__(self, point_string: str) -> None:
        self.point_str = point_string
        self.point = self.point_str.split(",")
        self.error_string = ""
        self.valid = False
        self.coord = None

        if len(self.point) != 2:
            self.error = "Lat and Lon required, usa a comma to seperate"
            return

        try:
            self.coord = LatLon(float(self.point[0]), float(self.point[1]))
            if not self.coord.is_valid():
                self.error = "Coordinates are not valid, not in WGS84 datum"
                return
        except ValueError:
            self.error = "Coordinates are not valid, lat and lon sperated by a comma in signed degree format"
            return

        self.valid = True

    def is_valid(self) -> tuple[bool, str]:
        return (self.valid, self.error)

    def point(self) -> Point:
        return self.coord

"""Time helpers — all internal times are minutes from an arbitrary day origin."""


def parse_time(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def format_time(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def travel_minutes(distance_km: float, speed_kmh: float) -> int:
    return round(distance_km * 60 / speed_kmh)

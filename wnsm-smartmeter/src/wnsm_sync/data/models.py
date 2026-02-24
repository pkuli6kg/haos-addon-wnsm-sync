"""Data models for energy readings."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MeasurementPoint:
    """A single interval energy measurement."""

    timestamp: datetime   # UTC start of the interval
    value_kwh: float      # Energy consumed in kWh
    obis_code: str        # e.g. "1-1:1.9.0"
    quality: str          # VAL, EST, SUB, …

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value_kwh": self.value_kwh,
            "obis_code": self.obis_code,
            "quality": self.quality,
        }

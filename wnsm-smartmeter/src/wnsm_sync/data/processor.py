"""Data processing logic for the WN Smart Meter API response."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .models import MeasurementPoint

logger = logging.getLogger(__name__)


class DataProcessor:
    """Converts raw API JSON into a list of MeasurementPoint objects."""

    def process(self, api_response: Dict[str, Any]) -> List[MeasurementPoint]:
        """Process the full API response.

        Expected structure::

            {
              "zaehlpunkt": "...",
              "zaehlwerke": [
                {
                  "obisCode": "1-1:1.9.0",
                  "messwerte": [
                    {
                      "zeitVon": "2024-01-01T00:00:00+00:00",
                      "zeitBis": "2024-01-01T00:15:00+00:00",
                      "messwert": 123.4,   # Wh
                      "qualitaet": "VAL"
                    },
                    ...
                  ]
                }
              ]
            }

        Args:
            api_response: Raw dict from the API.

        Returns:
            Sorted list of MeasurementPoint objects.
        """
        results: List[MeasurementPoint] = []

        zaehlwerke = api_response.get("zaehlwerke", [])
        if not zaehlwerke:
            logger.warning("No 'zaehlwerke' in API response")
            return results

        for zaehlwerk in zaehlwerke:
            obis_code = zaehlwerk.get("obisCode", "unknown")
            messwerte = zaehlwerk.get("messwerte", [])
            logger.debug("Processing %d messwerte for obisCode %s", len(messwerte), obis_code)

            for entry in messwerte:
                point = self._process_entry(entry, obis_code)
                if point is not None:
                    results.append(point)

        results.sort(key=lambda p: p.timestamp)
        logger.info("Processed %d measurement points", len(results))
        return results

    def _process_entry(
        self, entry: Dict[str, Any], obis_code: str
    ) -> MeasurementPoint | None:
        try:
            timestamp_str = entry.get("zeitVon")
            if not timestamp_str:
                logger.warning("Missing 'zeitVon' in entry: %s", entry)
                return None

            timestamp = self._parse_timestamp(timestamp_str)

            raw_value = entry.get("messwert")
            if raw_value is None:
                logger.warning("Missing 'messwert' in entry: %s", entry)
                return None

            value_kwh = float(raw_value) / 1000.0  # Wh → kWh
            quality = entry.get("qualitaet", "unknown")

            return MeasurementPoint(
                timestamp=timestamp,
                value_kwh=round(value_kwh, 6),
                obis_code=obis_code,
                quality=quality,
            )
        except Exception as exc:
            logger.warning("Failed to process entry %s: %s", entry, exc)
            return None

    @staticmethod
    def _parse_timestamp(ts: str) -> datetime:
        """Parse an ISO-8601 timestamp, normalising to UTC."""
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

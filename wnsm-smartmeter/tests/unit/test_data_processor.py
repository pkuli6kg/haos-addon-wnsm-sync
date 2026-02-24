"""Unit tests for DataProcessor."""

import sys
from datetime import timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wnsm_sync.data.models import MeasurementPoint
from wnsm_sync.data.processor import DataProcessor


def _make_response(messwerte, obis="1-1:1.9.0"):
    return {
        "zaehlpunkt": "AT001",
        "zaehlwerke": [
            {"obisCode": obis, "messwerte": messwerte}
        ],
    }


SAMPLE_MESSWERTE = [
    {"zeitVon": "2024-01-15T00:00:00+00:00", "zeitBis": "2024-01-15T00:15:00+00:00", "messwert": 234.0, "qualitaet": "VAL"},
    {"zeitVon": "2024-01-15T00:15:00+00:00", "zeitBis": "2024-01-15T00:30:00+00:00", "messwert": 187.0, "qualitaet": "EST"},
    {"zeitVon": "2024-01-15T00:30:00+00:00", "zeitBis": "2024-01-15T00:45:00+00:00", "messwert": 156.0, "qualitaet": "VAL"},
]


# ------------------------------------------------------------------
# process()
# ------------------------------------------------------------------


def test_process_returns_list_of_measurement_points():
    proc = DataProcessor()
    result = proc.process(_make_response(SAMPLE_MESSWERTE))
    assert isinstance(result, list)
    assert all(isinstance(p, MeasurementPoint) for p in result)


def test_process_wh_to_kwh_conversion():
    """234 Wh → 0.234 kWh."""
    proc = DataProcessor()
    result = proc.process(_make_response(SAMPLE_MESSWERTE))
    assert len(result) == 3
    assert abs(result[0].value_kwh - 0.234) < 1e-6
    assert abs(result[1].value_kwh - 0.187) < 1e-6
    assert abs(result[2].value_kwh - 0.156) < 1e-6


def test_process_parses_utc_timestamp():
    proc = DataProcessor()
    result = proc.process(_make_response(SAMPLE_MESSWERTE))
    ts = result[0].timestamp
    assert ts.tzinfo is not None
    assert ts.year == 2024
    assert ts.month == 1
    assert ts.day == 15
    assert ts.hour == 0


def test_process_preserves_obis_code():
    proc = DataProcessor()
    result = proc.process(_make_response(SAMPLE_MESSWERTE, obis="1-1:2.8.0"))
    for point in result:
        assert point.obis_code == "1-1:2.8.0"


def test_process_preserves_quality():
    proc = DataProcessor()
    result = proc.process(_make_response(SAMPLE_MESSWERTE))
    assert result[0].quality == "VAL"
    assert result[1].quality == "EST"


def test_process_results_are_sorted():
    reversed_messwerte = list(reversed(SAMPLE_MESSWERTE))
    proc = DataProcessor()
    result = proc.process(_make_response(reversed_messwerte))
    timestamps = [p.timestamp for p in result]
    assert timestamps == sorted(timestamps)


def test_process_empty_zaehlwerke_returns_empty():
    proc = DataProcessor()
    result = proc.process({"zaehlpunkt": "AT001", "zaehlwerke": []})
    assert result == []


def test_process_skips_entries_missing_zeitvon():
    bad_entry = {"zeitBis": "2024-01-15T00:15:00+00:00", "messwert": 100.0, "qualitaet": "VAL"}
    proc = DataProcessor()
    result = proc.process(_make_response([bad_entry] + SAMPLE_MESSWERTE))
    assert len(result) == 3  # bad entry skipped


def test_process_skips_entries_missing_messwert():
    bad_entry = {"zeitVon": "2024-01-15T00:00:00+00:00", "qualitaet": "VAL"}
    proc = DataProcessor()
    result = proc.process(_make_response([bad_entry] + SAMPLE_MESSWERTE))
    assert len(result) == 3


def test_process_multiple_zaehlwerke():
    response = {
        "zaehlpunkt": "AT001",
        "zaehlwerke": [
            {"obisCode": "1-1:1.9.0", "messwerte": SAMPLE_MESSWERTE[:2]},
            {"obisCode": "1-1:2.9.0", "messwerte": SAMPLE_MESSWERTE[2:]},
        ],
    }
    proc = DataProcessor()
    result = proc.process(response)
    assert len(result) == 3
    obis_codes = {p.obis_code for p in result}
    assert "1-1:1.9.0" in obis_codes
    assert "1-1:2.9.0" in obis_codes


# ------------------------------------------------------------------
# _parse_timestamp
# ------------------------------------------------------------------


def test_parse_timestamp_with_tz():
    ts = DataProcessor._parse_timestamp("2024-01-15T00:00:00+00:00")
    assert ts.tzinfo is not None


def test_parse_timestamp_without_tz_defaults_utc():
    ts = DataProcessor._parse_timestamp("2024-01-15T00:00:00")
    assert ts.tzinfo == timezone.utc


def test_parse_timestamp_z_suffix():
    ts = DataProcessor._parse_timestamp("2024-01-15T00:00:00Z")
    assert ts.tzinfo is not None

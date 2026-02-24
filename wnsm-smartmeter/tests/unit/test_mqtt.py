"""Unit tests for MQTT client and discovery."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wnsm_sync.config.loader import WNSMConfig
from wnsm_sync.data.models import MeasurementPoint
from wnsm_sync.mqtt.client import MQTTClient
from wnsm_sync.mqtt.discovery import HomeAssistantDiscovery


REQUIRED = dict(
    client_id="cid",
    client_secret="csec",
    api_key="akey",
    zp="AT0010000000000000001000004392265",
    mqtt_host="localhost",
)


def make_config(**kwargs) -> WNSMConfig:
    return WNSMConfig(**{**REQUIRED, **kwargs})


# ------------------------------------------------------------------
# MQTTClient – host parsing
# ------------------------------------------------------------------


def test_parse_plain_hostname():
    client = MQTTClient(make_config(mqtt_host="broker"))
    assert client._hostname == "broker"
    assert client._port == 1883


def test_parse_hostname_with_port():
    client = MQTTClient(make_config(mqtt_host="broker:1884"))
    assert client._hostname == "broker"
    assert client._port == 1884


def test_parse_url_with_port():
    client = MQTTClient(make_config(mqtt_host="mqtt://broker.example.com:1885"))
    assert client._hostname == "broker.example.com"
    assert client._port == 1885


# ------------------------------------------------------------------
# MQTTClient – auth
# ------------------------------------------------------------------


def test_no_auth_when_no_credentials():
    client = MQTTClient(make_config())
    assert client._auth is None


def test_auth_when_credentials_present():
    client = MQTTClient(make_config(mqtt_username="u", mqtt_password="p"))
    assert client._auth == {"username": "u", "password": "p"}


# ------------------------------------------------------------------
# MQTTClient – publish_message
# ------------------------------------------------------------------


@patch("paho.mqtt.publish.single")
def test_publish_message_success(mock_pub):
    mock_pub.return_value = None
    client = MQTTClient(make_config())
    result = client.publish_message("t/topic", {"key": "val"})
    assert result is True
    call_kwargs = mock_pub.call_args[1]
    assert call_kwargs["topic"] == "t/topic"
    payload = json.loads(call_kwargs["payload"])
    assert payload["key"] == "val"
    assert call_kwargs["hostname"] == "localhost"
    assert call_kwargs["port"] == 1883
    assert call_kwargs["retain"] is False


@patch("paho.mqtt.publish.single")
def test_publish_message_retain(mock_pub):
    mock_pub.return_value = None
    client = MQTTClient(make_config())
    client.publish_message("t/topic", {}, retain=True)
    assert mock_pub.call_args[1]["retain"] is True


@patch("paho.mqtt.publish.single")
def test_publish_message_retries_on_failure(mock_pub):
    mock_pub.side_effect = [Exception("conn"), None]
    client = MQTTClient(make_config(retry_count=1, retry_delay=0))
    result = client.publish_message("t/topic", {})
    assert result is True
    assert mock_pub.call_count == 2


@patch("paho.mqtt.publish.single")
def test_publish_message_fails_after_retries(mock_pub):
    mock_pub.side_effect = Exception("conn")
    client = MQTTClient(make_config(retry_count=1, retry_delay=0))
    result = client.publish_message("t/topic", {})
    assert result is False


# ------------------------------------------------------------------
# MQTTClient – publish_measurement
# ------------------------------------------------------------------


@patch("paho.mqtt.publish.single")
def test_publish_measurement_payload_format(mock_pub):
    mock_pub.return_value = None
    cfg = make_config(mqtt_topic="energy/state")
    client = MQTTClient(cfg)

    point = MeasurementPoint(
        timestamp=datetime(2024, 1, 15, 0, 15, tzinfo=timezone.utc),
        value_kwh=0.234,
        obis_code="1-1:1.9.0",
        quality="VAL",
    )
    result = client.publish_measurement(point)
    assert result is True

    payload = json.loads(mock_pub.call_args[1]["payload"])
    assert payload["value_kwh"] == 0.234
    assert payload["obis_code"] == "1-1:1.9.0"
    assert payload["quality"] == "VAL"
    assert "2024-01-15" in payload["timestamp"]


# ------------------------------------------------------------------
# HomeAssistantDiscovery
# ------------------------------------------------------------------


def test_energy_sensor_config_structure():
    disc = HomeAssistantDiscovery(make_config())
    cfg = disc.create_energy_sensor_config()

    assert "topic" in cfg
    assert cfg["topic"].startswith("homeassistant/sensor/")
    sensor = cfg["config"]
    assert sensor["device_class"] == "energy"
    assert sensor["state_class"] == "measurement"
    assert sensor["unit_of_measurement"] == "kWh"
    assert "value_json.value_kwh" in sensor["value_template"]
    assert sensor["device"]["manufacturer"] == "Wiener Netze"


def test_status_sensor_config_structure():
    disc = HomeAssistantDiscovery(make_config())
    cfg = disc.create_status_sensor_config()
    assert "topic" in cfg
    assert "value_json.status" in cfg["config"]["value_template"]


def test_get_all_discovery_configs_returns_two():
    disc = HomeAssistantDiscovery(make_config())
    all_cfgs = disc.get_all_discovery_configs()
    assert len(all_cfgs) == 2
    for item in all_cfgs:
        assert "topic" in item
        assert "config" in item

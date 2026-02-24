"""Unit tests for configuration loading."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wnsm_sync.config.loader import ConfigLoader, WNSMConfig


REQUIRED = dict(
    client_id="my-client",
    client_secret="my-secret",
    api_key="my-api-key",
    mqtt_host="localhost",
)


# ------------------------------------------------------------------
# WNSMConfig dataclass
# ------------------------------------------------------------------


def test_valid_config():
    cfg = WNSMConfig(**REQUIRED)
    assert cfg.client_id == "my-client"
    assert cfg.mqtt_port == 1883
    assert cfg.update_interval == 86400
    assert cfg.wertetyp == "QUARTER_HOUR"
    assert cfg.use_mock_data is False


def test_missing_client_id_raises():
    with pytest.raises(ValueError, match="CLIENT_ID"):
        WNSMConfig(**{**REQUIRED, "client_id": ""})


def test_missing_client_secret_raises():
    with pytest.raises(ValueError, match="CLIENT_SECRET"):
        WNSMConfig(**{**REQUIRED, "client_secret": ""})


def test_missing_api_key_raises():
    with pytest.raises(ValueError, match="API_KEY"):
        WNSMConfig(**{**REQUIRED, "api_key": ""})


def test_zp_is_optional():
    # ZP is optional — auto-discovered at runtime if omitted
    cfg = WNSMConfig(**{k: v for k, v in REQUIRED.items() if k != "zp"})
    assert cfg.zp is None


def test_missing_mqtt_host_raises():
    with pytest.raises(ValueError, match="MQTT_HOST"):
        WNSMConfig(**{**REQUIRED, "mqtt_host": ""})


def test_invalid_mqtt_port_raises():
    with pytest.raises(ValueError, match="MQTT_PORT"):
        WNSMConfig(**{**REQUIRED, "mqtt_port": 0})


def test_update_interval_too_small_raises():
    with pytest.raises(ValueError, match="UPDATE_INTERVAL"):
        WNSMConfig(**{**REQUIRED, "update_interval": 30})


# ------------------------------------------------------------------
# ConfigLoader
# ------------------------------------------------------------------


def _write_options(data: dict) -> str:
    """Write *data* to a temp JSON file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def test_loader_reads_options_file():
    options = {
        "CLIENT_ID": "opt-client",
        "CLIENT_SECRET": "opt-secret",
        "API_KEY": "opt-api-key",
        "ZP": "AT001",
        "MQTT_HOST": "broker",
        "DEBUG": True,
    }
    path = _write_options(options)
    try:
        original = ConfigLoader.OPTIONS_FILE
        ConfigLoader.OPTIONS_FILE = path
        cfg = ConfigLoader().load()
        assert cfg.client_id == "opt-client"
        assert cfg.mqtt_host == "broker"
        assert cfg.debug is True
    finally:
        ConfigLoader.OPTIONS_FILE = original
        os.unlink(path)


def test_loader_falls_back_to_env(monkeypatch):
    """When options.json is absent, env vars should be used."""
    monkeypatch.setenv("CLIENT_ID", "env-client")
    monkeypatch.setenv("CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("API_KEY", "env-key")
    monkeypatch.setenv("ZP", "AT002")
    monkeypatch.setenv("MQTT_HOST", "env-broker")

    original = ConfigLoader.OPTIONS_FILE
    ConfigLoader.OPTIONS_FILE = "/nonexistent/options.json"
    try:
        cfg = ConfigLoader().load()
        assert cfg.client_id == "env-client"
        assert cfg.zp == "AT002"
    finally:
        ConfigLoader.OPTIONS_FILE = original


def test_loader_converts_int_fields():
    options = {**REQUIRED, "MQTT_PORT": "1884", "UPDATE_INTERVAL": "7200"}
    path = _write_options({k.upper(): v for k, v in options.items()})
    try:
        original = ConfigLoader.OPTIONS_FILE
        ConfigLoader.OPTIONS_FILE = path
        cfg = ConfigLoader().load()
        assert cfg.mqtt_port == 1884
        assert cfg.update_interval == 7200
    finally:
        ConfigLoader.OPTIONS_FILE = original
        os.unlink(path)


def test_loader_converts_bool_fields():
    options = {**REQUIRED, "USE_MOCK_DATA": "true", "DEBUG": "false"}
    path = _write_options({k.upper(): v for k, v in options.items()})
    try:
        original = ConfigLoader.OPTIONS_FILE
        ConfigLoader.OPTIONS_FILE = path
        cfg = ConfigLoader().load()
        assert cfg.use_mock_data is True
        assert cfg.debug is False
    finally:
        ConfigLoader.OPTIONS_FILE = original
        os.unlink(path)

"""Configuration loading and validation."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class WNSMConfig:
    """Configuration for WNSM Sync."""

    # Required
    client_id: str
    client_secret: str
    api_key: str
    zp: str
    mqtt_host: str

    # Optional with defaults
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_topic: str = "smartmeter/energy/state"
    update_interval: int = 86400
    history_days: int = 1
    wertetyp: str = "QUARTER_HOUR"
    use_mock_data: bool = False
    retry_count: int = 3
    retry_delay: int = 10
    debug: bool = False

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not self.client_id:
            raise ValueError("CLIENT_ID is required")
        if not self.client_secret:
            raise ValueError("CLIENT_SECRET is required")
        if not self.api_key:
            raise ValueError("API_KEY is required")
        if not self.zp:
            raise ValueError("ZP (Zählpunkt) is required")
        if not self.mqtt_host:
            raise ValueError("MQTT_HOST is required")
        if not (1 <= self.mqtt_port <= 65535):
            raise ValueError("MQTT_PORT must be between 1 and 65535")
        if self.update_interval < 60:
            raise ValueError("UPDATE_INTERVAL must be at least 60 seconds")
        if self.history_days < 1:
            raise ValueError("HISTORY_DAYS must be at least 1")


class ConfigLoader:
    """Loads configuration from /data/options.json or environment variables."""

    OPTIONS_FILE = "/data/options.json"

    # Maps dataclass field name → list of env var names to check
    ENV_MAPPINGS: Dict[str, list] = {
        "client_id": ["CLIENT_ID"],
        "client_secret": ["CLIENT_SECRET"],
        "api_key": ["API_KEY"],
        "zp": ["ZP"],
        "mqtt_host": ["MQTT_HOST"],
        "mqtt_port": ["MQTT_PORT"],
        "mqtt_username": ["MQTT_USERNAME"],
        "mqtt_password": ["MQTT_PASSWORD"],
        "mqtt_topic": ["MQTT_TOPIC"],
        "update_interval": ["UPDATE_INTERVAL"],
        "history_days": ["HISTORY_DAYS"],
        "wertetyp": ["WERTETYP"],
        "use_mock_data": ["USE_MOCK_DATA"],
        "retry_count": ["RETRY_COUNT"],
        "retry_delay": ["RETRY_DELAY"],
        "debug": ["DEBUG"],
    }

    INT_FIELDS = {"mqtt_port", "update_interval", "history_days", "retry_count", "retry_delay"}
    BOOL_FIELDS = {"use_mock_data", "debug"}

    def load(self) -> WNSMConfig:
        """Load configuration from options.json, then environment variables."""
        config: Dict[str, Any] = {}
        self._load_from_options_file(config)
        self._load_from_environment(config)
        self._convert_types(config)
        self._log_config(config)

        valid_fields = set(WNSMConfig.__dataclass_fields__.keys())
        filtered = {k: v for k, v in config.items() if k in valid_fields}
        return WNSMConfig(**filtered)

    def _load_from_options_file(self, config: Dict[str, Any]):
        if not os.path.exists(self.OPTIONS_FILE):
            logger.warning("Options file %s not found, falling back to environment variables", self.OPTIONS_FILE)
            return
        try:
            with open(self.OPTIONS_FILE) as f:
                options = json.load(f)
            for key, value in options.items():
                config[key.lower()] = value
            logger.info("Loaded configuration from %s", self.OPTIONS_FILE)
        except Exception as exc:
            logger.error("Failed to load options.json: %s", exc)

    def _load_from_environment(self, config: Dict[str, Any]):
        for field, env_vars in self.ENV_MAPPINGS.items():
            if field in config and config[field]:
                continue
            for env_var in env_vars:
                val = os.environ.get(env_var)
                if val:
                    config[field] = val
                    break

    def _convert_types(self, config: Dict[str, Any]):
        for key, value in config.items():
            if value is None:
                continue
            if key in self.INT_FIELDS:
                try:
                    config[key] = int(value)
                except (ValueError, TypeError):
                    logger.warning("Cannot convert %s=%r to int", key, value)
            elif key in self.BOOL_FIELDS:
                if isinstance(value, str):
                    config[key] = value.lower() in ("true", "1", "yes", "on")
                else:
                    config[key] = bool(value)

    def _log_config(self, config: Dict[str, Any]):
        if not logger.isEnabledFor(logging.DEBUG):
            return
        for key, value in config.items():
            if "secret" in key.lower() or "password" in key.lower():
                logger.debug("  %s: ****", key)
            else:
                logger.debug("  %s: %s", key, value)

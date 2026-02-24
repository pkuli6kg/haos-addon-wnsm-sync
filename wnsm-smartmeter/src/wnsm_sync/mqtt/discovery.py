"""Home Assistant MQTT Discovery configuration."""

import logging
from typing import Any, Dict, List

from ..config.loader import WNSMConfig

logger = logging.getLogger(__name__)


class HomeAssistantDiscovery:
    """Generates MQTT discovery payloads for Home Assistant."""

    def __init__(self, config: WNSMConfig):
        self.config = config

    def _device(self) -> Dict[str, Any]:
        zp = self.config.zp or "unknown"
        suffix = zp[-8:]
        return {
            "identifiers": [f"wnsm_{zp}"],
            "name": f"Wiener Netze Smart Meter {suffix}",
            "model": "Smart Meter",
            "manufacturer": "Wiener Netze",
        }

    def _availability(self) -> Dict[str, str]:
        return {
            "topic": f"{self.config.mqtt_topic}/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
        }

    def create_energy_sensor_config(self) -> Dict[str, Any]:
        """Discovery config for the per-interval energy sensor."""
        suffix = self.config.zp[-8:]
        sensor_id = f"wnsm_energy_{suffix}"
        return {
            "topic": f"homeassistant/sensor/{sensor_id}/config",
            "config": {
                "name": "WNSM Energy",
                "object_id": sensor_id,
                "unique_id": sensor_id,
                "state_topic": self.config.mqtt_topic,
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "measurement",
                "value_template": "{{ value_json.value_kwh }}",
                "json_attributes_topic": self.config.mqtt_topic,
                "json_attributes_template": (
                    "{{ {'timestamp': value_json.timestamp, "
                    "'obis_code': value_json.obis_code, "
                    "'quality': value_json.quality} | tojson }}"
                ),
                "icon": "mdi:flash",
                "device": self._device(),
                "availability": self._availability(),
            },
        }

    def create_status_sensor_config(self) -> Dict[str, Any]:
        """Discovery config for the sync-status sensor."""
        suffix = self.config.zp[-8:]
        sensor_id = f"wnsm_sync_status_{suffix}"
        return {
            "topic": f"homeassistant/sensor/{sensor_id}/config",
            "config": {
                "name": "WNSM Sync Status",
                "object_id": sensor_id,
                "unique_id": sensor_id,
                "state_topic": f"{self.config.mqtt_topic}/status",
                "value_template": "{{ value_json.status }}",
                "json_attributes_topic": f"{self.config.mqtt_topic}/status",
                "json_attributes_template": (
                    "{{ {'last_sync': value_json.last_sync, "
                    "'next_sync': value_json.next_sync, "
                    "'error': value_json.error} | tojson }}"
                ),
                "icon": "mdi:sync",
                "device": self._device(),
            },
        }

    def get_all_discovery_configs(self) -> List[Dict[str, Any]]:
        return [
            self.create_energy_sensor_config(),
            self.create_status_sensor_config(),
        ]

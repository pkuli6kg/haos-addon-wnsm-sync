"""MQTT client for publishing energy data."""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import paho.mqtt.publish as publish

from ..config.loader import WNSMConfig
from ..data.models import MeasurementPoint

logger = logging.getLogger(__name__)


class MQTTClient:
    """Publishes energy measurements to an MQTT broker."""

    def __init__(self, config: WNSMConfig):
        self.config = config
        self._auth = self._prepare_auth()
        self._hostname, self._port = self._parse_host()

    def _prepare_auth(self) -> Optional[Dict[str, str]]:
        if self.config.mqtt_username and self.config.mqtt_password:
            return {
                "username": self.config.mqtt_username,
                "password": self.config.mqtt_password,
            }
        return None

    def _parse_host(self) -> Tuple[str, int]:
        host = self.config.mqtt_host
        if "://" in host:
            parsed = urlparse(host)
            return parsed.hostname or host, parsed.port or self.config.mqtt_port
        if ":" in host:
            h, p = host.rsplit(":", 1)
            try:
                return h, int(p)
            except ValueError:
                pass
        return host, self.config.mqtt_port

    # ------------------------------------------------------------------

    def publish_raw(self, topic: str, payload: str, retain: bool = False) -> bool:
        """Publish a raw string payload."""
        return self._publish(topic, payload, retain)

    def publish_message(
        self, topic: str, payload: Dict[str, Any], retain: bool = False
    ) -> bool:
        """Publish a JSON-serialised dict payload."""
        return self._publish(topic, json.dumps(payload), retain)

    def publish_measurement(self, point: MeasurementPoint) -> bool:
        """Publish a single MeasurementPoint as JSON."""
        payload = {
            "value_kwh": point.value_kwh,
            "timestamp": point.timestamp.isoformat(),
            "obis_code": point.obis_code,
            "quality": point.quality,
        }
        return self.publish_message(self.config.mqtt_topic, payload)

    def publish_discovery(self, discovery_config: Dict[str, Any]) -> bool:
        topic = discovery_config.get("topic")
        config = discovery_config.get("config", {})
        if not topic:
            logger.error("Discovery config missing 'topic'")
            return False
        return self.publish_message(topic, config)

    # ------------------------------------------------------------------

    def _publish(self, topic: str, payload: str, retain: bool) -> bool:
        for attempt in range(self.config.retry_count + 1):
            try:
                publish.single(
                    topic=topic,
                    payload=payload,
                    hostname=self._hostname,
                    port=self._port,
                    auth=self._auth,
                    retain=retain,
                )
                logger.debug("Published to %s", topic)
                return True
            except Exception as exc:
                if attempt < self.config.retry_count:
                    logger.warning(
                        "Publish attempt %d/%d failed (%s), retrying…",
                        attempt + 1,
                        self.config.retry_count + 1,
                        exc,
                    )
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error("Failed to publish to %s: %s", topic, exc)
        return False

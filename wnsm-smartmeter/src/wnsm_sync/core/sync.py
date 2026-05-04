"""Main synchronization orchestration."""

import logging
import time
from datetime import date, timedelta
from typing import List, Optional

from ..api.client import WNSMApiClient
from ..config.loader import WNSMConfig
from ..data.models import MeasurementPoint
from ..data.processor import DataProcessor
from ..mqtt.client import MQTTClient
from ..mqtt.discovery import HomeAssistantDiscovery
from .utils import with_retry

logger = logging.getLogger(__name__)


class WNSMSync:
    """Main synchronization orchestrator for WNSM data."""

    def __init__(self, config: WNSMConfig):
        self.config = config
        self.data_processor = DataProcessor()
        self.mqtt_client = MQTTClient(config)
        self.discovery = HomeAssistantDiscovery(config)
        self._api_client: Optional[WNSMApiClient] = None

    @property
    def api_client(self) -> WNSMApiClient:
        if self._api_client is None:
            self._api_client = WNSMApiClient(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                api_key=self.config.api_key,
                use_mock=self.config.use_mock_data,
            )
        return self._api_client

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def setup_discovery(self) -> bool:
        logger.info("Setting up Home Assistant MQTT discovery")
        configs = self.discovery.get_all_discovery_configs()
        results = [self.mqtt_client.publish_discovery(c) for c in configs]
        logger.info("Published %d/%d discovery configs", sum(results), len(results))
        return all(results)

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch_measurements(self) -> Optional[List[MeasurementPoint]]:
        """Authenticate (if needed) and fetch consumption data."""
        try:
            if not self.api_client.is_authenticated():
                with_retry(
                    self.api_client.authenticate,
                    self.config.retry_count,
                    self.config.retry_delay,
                )

            date_to = date.today()
            date_from = date_to - timedelta(days=self.config.history_days)

            logger.info("Fetching consumption from %s to %s", date_from, date_to)

            raw = with_retry(
                self.api_client.get_consumption,
                self.config.retry_count,
                self.config.retry_delay,
                self.config.zp,
                date_from,
                date_to,
                self.config.wertetyp,
            )

            measurements = self.data_processor.process(raw)
            logger.info("Fetched %d measurement points", len(measurements))
            return measurements

        except Exception as exc:
            logger.error("Failed to fetch measurements: %s", exc)
            if "auth" in str(exc).lower():
                self._api_client = None  # Force re-auth on next cycle
            return None

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish_measurements(self, measurements: List[MeasurementPoint]) -> bool:
        logger.info("Publishing %d measurements to MQTT", len(measurements))
        results = [
            self.mqtt_client.publish_measurement(m) for m in measurements
        ]
        ok = sum(results)
        logger.info("Published %d/%d measurements", ok, len(measurements))
        return ok == len(measurements)

    def publish_status(self, status: str, error: Optional[str] = None) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "status": status,
            "last_sync": now.isoformat(),
            "next_sync": (
                now + timedelta(seconds=self.config.update_interval)
            ).isoformat(),
            "error": error,
        }
        self.mqtt_client.publish_message(
            f"{self.config.mqtt_topic}/status", payload, retain=True
        )

    def publish_availability(self, available: bool) -> None:
        self.mqtt_client.publish_raw(
            f"{self.config.mqtt_topic}/availability",
            "online" if available else "offline",
            retain=True,
        )

    # ------------------------------------------------------------------
    # Sync cycle
    # ------------------------------------------------------------------

    def run_sync_cycle(self) -> bool:
        try:
            logger.info("Starting sync cycle")
            self.publish_status("running")
            self.publish_availability(True)

            measurements = self.fetch_measurements()
            if not measurements:
                self.publish_status("error", "Failed to fetch measurements")
                return False

            if not self.publish_measurements(measurements):
                self.publish_status("error", "Failed to publish some measurements")
                return False

            self.publish_status("success")
            logger.info("Sync cycle completed successfully")
            return True

        except Exception as exc:
            logger.error("Sync cycle failed: %s", exc)
            self.publish_status("error", str(exc))
            return False

    def run_continuous(self) -> None:
        logger.info("Starting continuous synchronization")
        self.setup_discovery()
        try:
            while True:
                self.run_sync_cycle()
                logger.info("Sleeping for %ds", self.config.update_interval)
                time.sleep(self.config.update_interval)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.publish_availability(False)

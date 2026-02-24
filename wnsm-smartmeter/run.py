#!/usr/bin/env python3
"""Entry point for the Wiener Netze Smart Meter Home Assistant Add-on."""

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from wnsm_sync.config.loader import ConfigLoader
from wnsm_sync.core.sync import WNSMSync
from wnsm_sync.core.utils import setup_logging

logger = logging.getLogger(__name__)


def main():
    try:
        config = ConfigLoader().load()
        setup_logging(config.debug)

        logger.info("Wiener Netze Smart Meter Add-on started")
        if config.use_mock_data:
            logger.warning("MOCK DATA MODE — using simulated data")

        WNSMSync(config).run_continuous()

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully")
        sys.exit(0)
    except Exception as exc:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Utility functions for core operations."""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def with_retry(func: Callable, retry_count: int, retry_delay: int, *args, **kwargs) -> Any:
    """Execute a function with retry logic and exponential back-off.

    Args:
        func: Function to execute.
        retry_count: Number of additional attempts after the first.
        retry_delay: Base delay in seconds between retries.
        *args / **kwargs: Passed through to *func*.

    Returns:
        Result of the successful function call.

    Raises:
        Exception: The last exception if all attempts fail.
    """
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt in range(retry_count + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < retry_count:
                delay = min(retry_delay * (2 ** attempt), 300)
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %ds…",
                    attempt + 1,
                    retry_count + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error("All %d attempts failed", retry_count + 1)

    raise last_exc


def setup_logging(debug: bool = False) -> None:
    """Configure root logger."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    if debug:
        logger.debug("Debug logging enabled")

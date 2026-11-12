"""
Exponential backoff with full jitter strategy for transient AWS Kinesis throttling.
"""
import random
import time
import logging

logger = logging.getLogger(__name__)


class BackoffPolicy:
    """Calculates exponential backoff delay with full jitter."""

    def __init__(self, base_delay: float = 0.2, max_delay: float = 5.0):
        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate_delay(self, attempt: int) -> float:
        """
        AWS Full Jitter: Sleep = uniform(0, min(max_delay, base_delay * 2^attempt))
        """
        temp = min(self.max_delay, self.base_delay * (2 ** attempt))
        delay = random.uniform(0, temp)
        return round(delay, 4)

    def sleep(self, attempt: int):
        delay = self.calculate_delay(attempt)
        logger.warning(f"Throttling or partial batch failure encountered. Backing off for {delay:.3f}s (Attempt {attempt}).")
        time.sleep(delay)

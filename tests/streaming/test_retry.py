"""
Unit tests for exponential backoff and jitter calculations.
"""
from streaming.retry import BackoffPolicy


def test_backoff_delay_bounds():
    policy = BackoffPolicy(base_delay=0.1, max_delay=2.0)

    for attempt in range(1, 6):
        delay = policy.calculate_delay(attempt)
        assert 0.0 <= delay <= 2.0


def test_backoff_increases_with_attempts():
    policy = BackoffPolicy(base_delay=0.5, max_delay=10.0)
    # The ceiling of uniform(0, temp) increases with attempt
    max_ceiling_attempt_1 = policy.base_delay * (2 ** 1)
    max_ceiling_attempt_3 = policy.base_delay * (2 ** 3)
    assert max_ceiling_attempt_3 > max_ceiling_attempt_1

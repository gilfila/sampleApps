"""Circuit breaker for Workday API calls.

Prevents retry storms when Workday is unavailable by tracking consecutive
failures and blocking calls during a cooldown period.
"""

import time
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for Workday API calls.

    States:
        closed   - Normal operation, calls proceed.
        open     - Too many failures, calls are blocked.
        half-open - Cooldown elapsed, one trial call is allowed.
    """

    def __init__(self, failure_threshold=5, cooldown_seconds=300):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'

    def can_proceed(self):
        """Check if a call should be attempted."""
        if self.state == 'closed':
            return True

        # Check if cooldown has elapsed
        if self.last_failure_time and time.time() - self.last_failure_time >= self.cooldown_seconds:
            self.state = 'half-open'
            logger.info("Circuit breaker entering half-open state")
            return True

        return False

    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = 'closed'

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Cooldown: {self.cooldown_seconds}s"
            )

    @property
    def is_open(self):
        """True when the breaker is open and cooldown has NOT elapsed."""
        return self.state == 'open' and not self.can_proceed()

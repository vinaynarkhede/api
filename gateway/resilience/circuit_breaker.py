"""Circuit breaker pattern implementation."""
import time
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

from shared.exceptions import CircuitBreakerOpen, ServiceUnavailable


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changed_at: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern.

    Prevents cascading failures by stopping requests to a failing service
    and allowing it time to recover.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from function
        """
        # Check circuit state
        self._check_and_update_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service is unavailable. Try again later."
            )

        # Allow limited calls in half-open state
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is HALF-OPEN and at capacity."
                )
            self.half_open_calls += 1

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _check_and_update_state(self) -> None:
        """Check and update circuit state based on timeout."""
        now = time.time()

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            time_since_state_change = now - self.stats.state_changed_at

            if time_since_state_change >= self.timeout_seconds:
                # Move to half-open state
                self._transition_to_half_open()

    def _on_success(self) -> None:
        """Handle successful call."""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # If we've had enough successes, close the circuit
            if self.stats.successful_requests >= self.half_open_max_calls:
                self._transition_to_closed()

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state opens the circuit again
            self._transition_to_open()

        elif self.state == CircuitState.CLOSED:
            # Check if we've hit the failure threshold
            if self.stats.consecutive_failures >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.stats.consecutive_failures = 0
        self.stats.state_changed_at = time.time()
        self.half_open_calls = 0

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.stats.state_changed_at = time.time()
        self.half_open_calls = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF-OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.stats.state_changed_at = time.time()
        self.stats.successful_requests = 0
        self.half_open_calls = 0

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.half_open_calls = 0

    def get_state(self) -> dict:
        """
        Get current state and statistics.

        Returns:
            Dict with state information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "consecutive_failures": self.stats.consecutive_failures,
            "failure_rate": (
                self.stats.failed_requests / self.stats.total_requests
                if self.stats.total_requests > 0 else 0
            ),
            "state_changed_at": datetime.fromtimestamp(self.stats.state_changed_at).isoformat(),
        }


class CircuitBreakerRegistry:
    """Registry to manage multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker registry."""
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            failure_threshold: Failure threshold
            timeout_seconds: Timeout in seconds

        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout_seconds=timeout_seconds,
            )

        return self.breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.breakers.get(name)

    def get_all_states(self) -> dict:
        """Get states of all circuit breakers."""
        return {
            name: breaker.get_state()
            for name, breaker in self.breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()

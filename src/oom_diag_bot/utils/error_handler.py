"""Error handling and retry mechanisms."""

import asyncio
import random
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: list[type[Exception]] | None = None,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            retryable_exceptions: List of exceptions that should trigger retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
        ]


def retry_async(config: RetryConfig = None):
    """Decorator for adding retry logic to async functions.

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if exception is retryable
                    if not any(
                        isinstance(e, exc_type)
                        for exc_type in config.retryable_exceptions
                    ):
                        logger.error(
                            "Non-retryable exception occurred",
                            function=func.__name__,
                            exception=str(e),
                            attempt=attempt + 1,
                        )
                        raise

                    # Don't retry on last attempt
                    if attempt == config.max_attempts - 1:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )

                    # Add jitter if enabled
                    if config.jitter:
                        delay *= 0.5 + random.random() * 0.5

                    logger.warning(
                        "Retrying after exception",
                        function=func.__name__,
                        exception=str(e),
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        delay=delay,
                    )

                    await asyncio.sleep(delay)

            # If we get here, all attempts failed
            logger.error(
                "All retry attempts failed",
                function=func.__name__,
                exception=str(last_exception),
                attempts=config.max_attempts,
            )
            raise last_exception

        return wrapper

    return decorator


async def timeout_wrapper(
    coro: Callable[..., Any], timeout_seconds: float, *args, **kwargs
) -> Any:
    """Wrap a coroutine with timeout handling.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        *args: Arguments to pass to coroutine
        **kwargs: Keyword arguments to pass to coroutine

    Returns:
        Result of coroutine execution

    Raises:
        asyncio.TimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout_seconds)
    except TimeoutError:
        logger.error(
            "Operation timed out", function=coro.__name__, timeout=timeout_seconds
        )
        raise


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to monitor
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator implementation."""

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                    logger.info("Circuit breaker attempting recovery")
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        import time

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "closed"
        logger.info("Circuit breaker reset to closed state")

    def _on_failure(self) -> None:
        """Handle failed operation."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class GracefulShutdownHandler:
    """Handle graceful shutdown of async operations."""

    def __init__(self):
        """Initialize shutdown handler."""
        self.shutdown_event = asyncio.Event()
        self.running_tasks = set()

    def add_task(self, task: asyncio.Task) -> None:
        """Add a task to be tracked for shutdown.

        Args:
            task: Task to track
        """
        self.running_tasks.add(task)
        task.add_done_callback(self.running_tasks.discard)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown all running tasks.

        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        logger.info("Starting graceful shutdown", task_count=len(self.running_tasks))

        # Signal shutdown to all components
        self.shutdown_event.set()

        # Wait for tasks to complete or timeout
        if self.running_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.running_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "Graceful shutdown timeout, canceling remaining tasks",
                    task_count=len(self.running_tasks),
                )

                # Cancel remaining tasks
                for task in self.running_tasks:
                    task.cancel()

                # Wait a bit for cancellations to complete
                await asyncio.sleep(1.0)

        logger.info("Graceful shutdown completed")

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated.

        Returns:
            True if shutdown is in progress
        """
        return self.shutdown_event.is_set()

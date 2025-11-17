"""Structured logging setup utilities."""

import logging
from typing import Any

import structlog


def setup_structured_logging(
    log_level: str = "INFO", debug_mode: bool = False, enable_json: bool = True
) -> None:
    """Configure structured logging with consistent formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug_mode: Enable debug-friendly console output
        enable_json: Use JSON formatter for production logs
    """
    # Configure standard library logging
    logging.basicConfig(level=getattr(logging, log_level.upper()), format="%(message)s")

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Choose output format based on environment
    if debug_mode or not enable_json:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def add_context_filter(context: dict[str, Any]) -> None:
    """Add global context to all log messages.

    Args:
        context: Dictionary of context to add to logs
    """
    # Add context to all future log messages
    for key, value in context.items():
        structlog.contextvars.bind_contextvars(**{key: value})


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter health check messages.

        Args:
            record: Log record to check

        Returns:
            False if record should be filtered out
        """
        message = record.getMessage()
        return "/health" not in message and "health_check" not in message


class MetricsFilter(logging.Filter):
    """Filter out metrics collection requests from logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter metrics messages.

        Args:
            record: Log record to check

        Returns:
            False if record should be filtered out
        """
        message = record.getMessage()
        return "/metrics" not in message and "metrics_collection" not in message

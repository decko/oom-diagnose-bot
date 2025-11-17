"""Configuration loader and validation."""

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)


def parse_comma_separated_string(v):
    """Parse comma-separated string into list."""
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v


class BotConfig(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Slack Configuration
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_app_token: str = Field(..., env="SLACK_APP_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")

    # OpenShift Configuration
    openshift_token: str | None = Field(None, env="OPENSHIFT_TOKEN")
    openshift_api_url: str | None = Field(None, env="OPENSHIFT_API_URL")

    # Prometheus Configuration
    prometheus_url: str | None = Field(None, env="PROMETHEUS_URL")
    prometheus_token: str | None = Field(None, env="PROMETHEUS_TOKEN")

    # AWS Configuration
    aws_access_key_id: str | None = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field("us-east-1", env="AWS_DEFAULT_REGION")

    # Bot Configuration
    monitored_channels: str = Field("", env="MONITORED_CHANNELS")
    oom_keywords: str = Field(
        "OOMKilled,memory limit exceeded,killed due to memory", env="OOM_KEYWORDS"
    )
    debug_mode: bool = Field(False, env="DEBUG_MODE")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Performance Configuration
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    max_concurrent_requests: int = Field(10, env="MAX_CONCURRENT_REQUESTS")

    @property
    def monitored_channels_list(self) -> list[str]:
        """Get monitored channels as a list."""
        return parse_comma_separated_string(self.monitored_channels)

    @property
    def oom_keywords_list(self) -> list[str]:
        """Get OOM keywords as a list."""
        return parse_comma_separated_string(self.oom_keywords)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


def load_config() -> BotConfig:
    """Load and validate configuration."""
    try:
        config = BotConfig()
        logger.info(
            "Configuration loaded",
            monitored_channels=len(config.monitored_channels),
            debug_mode=config.debug_mode,
            log_level=config.log_level,
        )
        return config
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        raise


def validate_required_config(config: BotConfig) -> None:
    """Validate required configuration is present."""
    errors = []

    # Check Slack configuration
    if not config.slack_bot_token:
        errors.append("SLACK_BOT_TOKEN is required")
    if not config.slack_app_token:
        errors.append("SLACK_APP_TOKEN is required")
    if not config.slack_signing_secret:
        errors.append("SLACK_SIGNING_SECRET is required")

    # Check monitored channels
    if not config.monitored_channels_list:
        errors.append("At least one monitored channel must be configured")

    # Validate channel format
    import re

    for channel in config.monitored_channels_list:
        if not re.match(r"^C[A-Z0-9]{8,}$", channel):
            errors.append(f"Invalid channel ID format: {channel}")

    # Warn about missing optional services
    warnings = []
    if not config.openshift_token or not config.openshift_api_url:
        warnings.append(
            "OpenShift configuration missing - OpenShift data will not be available"
        )

    if not config.prometheus_url:
        warnings.append(
            "Prometheus configuration missing - metrics data will not be available"
        )

    if not config.aws_access_key_id or not config.aws_secret_access_key:
        warnings.append(
            "AWS configuration missing - CloudWatch logs will not be available"
        )

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    for warning in warnings:
        logger.warning(warning)


def setup_logging(config: BotConfig) -> None:
    """Setup structured logging."""
    import structlog
    from structlog.stdlib import LoggerFactory

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if not config.debug_mode
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set log level
    import logging

    logging.basicConfig(level=getattr(logging, config.log_level))

    logger.info(
        "Logging configured", level=config.log_level, debug_mode=config.debug_mode
    )

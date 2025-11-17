"""Bot Configuration model."""

from pydantic import BaseModel, Field, field_validator


class BotConfiguration(BaseModel):
    """Bot operational configuration and settings."""

    monitored_channels: list[str] = Field(
        ..., description="List of Slack channel IDs to monitor"
    )
    oom_keywords: list[str] = Field(
        ..., description="List of keywords that trigger OOM detection"
    )
    response_template: str = Field(
        "", description="Template for diagnostic report formatting"
    )
    rate_limit_per_minute: int = Field(
        60, description="Maximum responses per minute", ge=1, le=1000
    )
    debug_mode: bool = Field(False, description="Enable detailed logging and debugging")
    health_check_interval: int = Field(
        30, description="Health check frequency in seconds", ge=10, le=300
    )

    @field_validator("monitored_channels")
    @classmethod
    def validate_monitored_channels(cls, v: list[str]) -> list[str]:
        """Validate Slack channel IDs."""
        import re

        for channel_id in v:
            if not re.match(r"^C[A-Z0-9]{8,}$", channel_id):
                raise ValueError(f"Invalid channel ID format: {channel_id}")
        return v

    @field_validator("oom_keywords")
    @classmethod
    def validate_oom_keywords(cls, v: list[str]) -> list[str]:
        """Validate OOM keywords."""
        if not v:
            raise ValueError("At least one OOM keyword must be configured")
        return [keyword.strip() for keyword in v if keyword.strip()]

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

"""CloudWatch Logs model for log entries."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Log level enumeration."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class CloudWatchLogs(BaseModel):
    """Log entries related to the OOM incident."""

    log_group: str = Field(..., description="CloudWatch log group name")
    log_stream: str | None = Field(None, description="CloudWatch log stream name")
    timestamp: datetime = Field(..., description="Log entry timestamp")
    message: str = Field(..., description="Log message content", max_length=10000)
    level: LogLevel = Field(..., description="Log level")
    source: str | None = Field(None, description="Log source identifier")

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, v: str) -> str:
        """Validate message length."""
        if len(v.encode("utf-8")) > 10000:
            raise ValueError("Log message too long")
        return v

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

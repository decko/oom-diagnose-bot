"""OOM Alert model for representing detected out-of-memory incidents."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class OOMAlert(BaseModel):
    """Represents a detected out-of-memory incident extracted from Slack messages."""

    message_id: str = Field(
        ..., description="Slack message identifier for threading responses"
    )
    channel_id: str = Field(..., description="Slack channel where alert was detected")
    timestamp: datetime = Field(..., description="Alert detection timestamp")
    raw_content: str = Field(
        ..., description="Original alert message content", max_length=40000
    )
    pod_name: str = Field(..., description="Extracted Kubernetes pod name")
    namespace: str = Field(..., description="Extracted Kubernetes namespace")
    container_name: str | None = Field(None, description="Extracted container name")
    keywords_matched: list[str] = Field(
        ..., description="List of OOM keywords that triggered detection"
    )
    user_id: str = Field(..., description="Slack user who posted the original alert")

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, v: str) -> str:
        """Validate Slack message ID format."""
        if not re.match(r"^\d+\.\d+$", v):
            raise ValueError("Invalid message ID format")
        return v

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        """Validate Slack channel ID format."""
        if not re.match(r"^C[A-Z0-9]{8,}$", v):
            raise ValueError("Invalid channel ID format")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate Slack user ID format."""
        if not re.match(r"^U[A-Z0-9]{8,}$", v):
            raise ValueError("Invalid user ID format")
        return v

    @field_validator("pod_name")
    @classmethod
    def validate_pod_name(cls, v: str) -> str:
        """Validate Kubernetes pod name format."""
        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid pod name format")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate Kubernetes namespace format."""
        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid namespace format")
        return v

    @field_validator("container_name")
    @classmethod
    def validate_container_name(cls, v: str | None) -> str | None:
        """Validate Kubernetes container name format."""
        if v is not None and not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid container name format")
        return v

    @field_validator("keywords_matched")
    @classmethod
    def validate_keywords_matched(cls, v: list[str]) -> list[str]:
        """Validate that at least one keyword was matched."""
        if not v:
            raise ValueError("At least one OOM keyword must be matched")
        return v

    @field_validator("raw_content")
    @classmethod
    def validate_raw_content_length(cls, v: str) -> str:
        """Validate raw content length."""
        if len(v.encode("utf-8")) > 40000:
            raise ValueError("Text too long")
        return v

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

    def __str__(self) -> str:
        """String representation of the alert."""
        return f"OOMAlert(pod={self.pod_name}, namespace={self.namespace}, ts={self.timestamp})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"OOMAlert(message_id={self.message_id}, pod_name={self.pod_name}, "
            f"namespace={self.namespace}, keywords={self.keywords_matched})"
        )

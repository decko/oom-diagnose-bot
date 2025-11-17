"""Data Source Configuration model."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AuthenticationType(str, Enum):
    """Authentication method enumeration."""

    TOKEN = "token"
    IAM = "iam"
    OAUTH = "oauth"


class DataSourceConfig(BaseModel):
    """Configuration for external data source connections."""

    name: str = Field(..., description="Data source identifier")
    enabled: bool = Field(True, description="Whether this data source is active")
    endpoint_url: str = Field(..., description="API endpoint URL")
    timeout_seconds: int = Field(
        30, description="Request timeout configuration", ge=1, le=300
    )
    retry_attempts: int = Field(
        3, description="Number of retry attempts for failed requests", ge=0, le=10
    )
    authentication_type: AuthenticationType = Field(
        ..., description="Authentication method"
    )
    connection_pool_size: int = Field(
        10, description="Maximum concurrent connections", ge=1, le=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate data source name."""
        if v not in {"openshift", "prometheus", "cloudwatch"}:
            raise ValueError("Invalid data source name")
        return v

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint URL must start with http:// or https://")
        return v

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

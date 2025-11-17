"""Container Information model for individual container details."""

from pydantic import BaseModel, Field, field_validator


class ContainerInformation(BaseModel):
    """Individual container details within a pod."""

    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image name and tag")
    memory_usage: int | None = Field(
        None, description="Current memory usage in bytes", ge=0
    )
    cpu_usage: int | None = Field(
        None, description="Current CPU usage in millicores", ge=0
    )
    restart_count: int = Field(0, description="Container-specific restart count", ge=0)
    last_termination_reason: str | None = Field(
        None, description="Reason for last termination"
    )
    ready: bool = Field(..., description="Container readiness status")
    started: bool = Field(..., description="Container started status")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate container name format."""
        import re

        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid container name format")
        return v

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str) -> str:
        """Validate container image format."""
        if not v.strip():
            raise ValueError("Container image cannot be empty")
        return v

    @property
    def memory_usage_mb(self) -> float | None:
        """Get memory usage in megabytes."""
        if self.memory_usage is None:
            return None
        return self.memory_usage / (1024 * 1024)

    @property
    def cpu_usage_cores(self) -> float | None:
        """Get CPU usage in cores."""
        if self.cpu_usage is None:
            return None
        return self.cpu_usage / 1000

    @property
    def is_oom_killed(self) -> bool:
        """Check if container was OOM killed."""
        return self.last_termination_reason == "OOMKilled"

    @property
    def is_healthy(self) -> bool:
        """Check if container is healthy (ready and started)."""
        return self.ready and self.started

    def format_status_summary(self) -> str:
        """Format container status summary."""
        status_parts = []

        if self.is_healthy:
            status_parts.append("Healthy")
        else:
            if not self.ready:
                status_parts.append("Not Ready")
            if not self.started:
                status_parts.append("Not Started")

        if self.restart_count > 0:
            status_parts.append(f"{self.restart_count} restarts")

        if self.last_termination_reason:
            status_parts.append(f"Last exit: {self.last_termination_reason}")

        return " | ".join(status_parts) if status_parts else "Unknown"

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

    def __str__(self) -> str:
        """String representation of container information."""
        return f"ContainerInformation(name={self.name}, ready={self.ready}, started={self.started})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ContainerInformation(name={self.name}, image={self.image}, "
            f"ready={self.ready}, started={self.started}, restarts={self.restart_count})"
        )

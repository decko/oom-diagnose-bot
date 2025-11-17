"""Pod Information model for Kubernetes pod metadata."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .container_information import ContainerInformation


class PodStatus(str, Enum):
    """Kubernetes pod status enumeration."""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class PodInformation(BaseModel):
    """Kubernetes pod metadata retrieved from OpenShift."""

    name: str = Field(..., description="Pod name")
    namespace: str = Field(..., description="Pod namespace")
    status: PodStatus = Field(..., description="Current pod status")
    memory_request: int | None = Field(
        None, description="Configured memory request in bytes", ge=0
    )
    memory_limit: int | None = Field(
        None, description="Configured memory limit in bytes", ge=0
    )
    cpu_request: int | None = Field(
        None, description="Configured CPU request in millicores", ge=0
    )
    cpu_limit: int | None = Field(
        None, description="Configured CPU limit in millicores", ge=0
    )
    creation_timestamp: datetime = Field(..., description="Pod creation time")
    restart_count: int = Field(0, description="Number of container restarts", ge=0)
    node_name: str | None = Field(None, description="Node where pod is scheduled")
    labels: dict[str, str] = Field(
        default_factory=dict, description="Pod labels as key-value pairs"
    )
    annotations: dict[str, str] = Field(
        default_factory=dict, description="Pod annotations as key-value pairs"
    )
    containers: list[ContainerInformation] = Field(
        default_factory=list, description="Container information within the pod"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate pod name format."""
        import re

        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid pod name format")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate namespace format."""
        import re

        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid namespace format")
        return v

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v: str | None) -> str | None:
        """Validate node name format."""
        if v is not None:
            import re

            if not re.match(
                r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$", v
            ):
                raise ValueError("Invalid node name format")
        return v

    @property
    def memory_request_mb(self) -> float | None:
        """Get memory request in megabytes."""
        if self.memory_request is None:
            return None
        return self.memory_request / (1024 * 1024)

    @property
    def memory_limit_mb(self) -> float | None:
        """Get memory limit in megabytes."""
        if self.memory_limit is None:
            return None
        return self.memory_limit / (1024 * 1024)

    @property
    def cpu_request_cores(self) -> float | None:
        """Get CPU request in cores."""
        if self.cpu_request is None:
            return None
        return self.cpu_request / 1000

    @property
    def cpu_limit_cores(self) -> float | None:
        """Get CPU limit in cores."""
        if self.cpu_limit is None:
            return None
        return self.cpu_limit / 1000

    @property
    def is_oom_killed(self) -> bool:
        """Check if any container was OOM killed."""
        return any(
            container.last_termination_reason == "OOMKilled"
            for container in self.containers
        )

    @property
    def total_restart_count(self) -> int:
        """Get total restart count across all containers."""
        return sum(container.restart_count for container in self.containers)

    @property
    def has_resource_limits(self) -> bool:
        """Check if pod has resource limits configured."""
        return self.memory_limit is not None or self.cpu_limit is not None

    def get_container(self, name: str) -> ContainerInformation | None:
        """Get container by name."""
        for container in self.containers:
            if container.name == name:
                return container
        return None

    def format_resource_summary(self) -> str:
        """Format resource configuration summary."""
        lines = []

        if self.memory_request is not None or self.memory_limit is not None:
            mem_req = (
                f"{self.memory_request_mb:.0f}Mi" if self.memory_request_mb else "None"
            )
            mem_lim = (
                f"{self.memory_limit_mb:.0f}Mi" if self.memory_limit_mb else "None"
            )
            lines.append(f"Memory: {mem_req} request / {mem_lim} limit")

        if self.cpu_request is not None or self.cpu_limit is not None:
            cpu_req = (
                f"{self.cpu_request_cores:.1f}" if self.cpu_request_cores else "None"
            )
            cpu_lim = f"{self.cpu_limit_cores:.1f}" if self.cpu_limit_cores else "None"
            lines.append(f"CPU: {cpu_req} request / {cpu_lim} limit")

        return "\n".join(lines) if lines else "No resource limits configured"

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

    def __str__(self) -> str:
        """String representation of pod information."""
        return f"PodInformation(name={self.name}, namespace={self.namespace}, status={self.status.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"PodInformation(name={self.name}, namespace={self.namespace}, "
            f"status={self.status.value}, containers={len(self.containers)})"
        )

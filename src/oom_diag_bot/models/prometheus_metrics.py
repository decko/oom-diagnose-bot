"""Prometheus Metrics model for memory and resource usage metrics."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PrometheusMetrics(BaseModel):
    """Memory and resource usage metrics from Prometheus."""

    pod_name: str = Field(..., description="Target pod name")
    namespace: str = Field(..., description="Target namespace")
    memory_usage_current: int | None = Field(
        None, description="Current memory usage in bytes", ge=0
    )
    memory_usage_average_1h: int | None = Field(
        None, description="Average memory usage over 1 hour", ge=0
    )
    memory_usage_peak_24h: int | None = Field(
        None, description="Peak memory usage in last 24 hours", ge=0
    )
    memory_limit: int | None = Field(None, description="Configured memory limit", ge=0)
    oom_kills_total: int = Field(0, description="Total OOM kills for this pod", ge=0)
    cpu_usage_current: float | None = Field(
        None, description="Current CPU usage percentage", ge=0, le=100
    )
    network_io_bytes: int | None = Field(None, description="Network I/O in bytes", ge=0)
    filesystem_usage_bytes: int | None = Field(
        None, description="Filesystem usage in bytes", ge=0
    )
    query_timestamp: datetime = Field(..., description="Metrics collection timestamp")

    @field_validator("pod_name", "namespace")
    @classmethod
    def validate_kubernetes_name(cls, v: str) -> str:
        """Validate Kubernetes naming convention."""
        import re

        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError("Invalid Kubernetes name format")
        return v

    @property
    def memory_usage_current_mb(self) -> float | None:
        """Get current memory usage in MB."""
        return (
            self.memory_usage_current / (1024 * 1024)
            if self.memory_usage_current
            else None
        )

    @property
    def memory_utilization_percent(self) -> float | None:
        """Calculate memory utilization percentage."""
        if self.memory_usage_current and self.memory_limit:
            return (self.memory_usage_current / self.memory_limit) * 100
        return None

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

"""Diagnostic Report model for structured diagnostic information."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .cloudwatch_logs import CloudWatchLogs
from .pod_information import PodInformation
from .prometheus_metrics import PrometheusMetrics


class ErrorInfo(BaseModel):
    """Error information for failed data source queries."""

    source: str = Field(..., description="Data source name")
    error: str = Field(..., description="Error message")
    timestamp: datetime = Field(..., description="Error occurrence timestamp")


class DiagnosticReport(BaseModel):
    """Contains structured diagnostic information collected from multiple sources."""

    alert_id: str = Field(..., description="Reference to originating OOMAlert")
    generation_timestamp: datetime = Field(..., description="Report creation timestamp")
    summary: str = Field(
        ..., description="Human-readable incident summary", max_length=2000
    )
    openshift_data: PodInformation | None = Field(
        None, description="Pod information from OpenShift API"
    )
    prometheus_metrics: PrometheusMetrics | None = Field(
        None, description="Memory usage metrics and trends"
    )
    cloudwatch_logs: list[CloudWatchLogs] = Field(
        default_factory=list,
        description="Relevant log entries from incident timeframe",
        max_items=50,
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Suggested remediation actions", max_items=10
    )
    data_sources_available: list[str] = Field(
        ..., description="List of successfully queried sources"
    )
    errors: list[ErrorInfo] = Field(
        default_factory=list, description="Collection errors from unavailable sources"
    )

    @field_validator("generation_timestamp")
    @classmethod
    def validate_generation_timestamp(cls, v: datetime) -> datetime:
        """Validate generation timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("Generation timestamp cannot be in the future")
        return v

    @field_validator("data_sources_available")
    @classmethod
    def validate_data_sources_available(cls, v: list[str]) -> list[str]:
        """Validate that at least one data source is available."""
        if not v:
            raise ValueError("At least one data source must be available")

        valid_sources = {"openshift", "prometheus", "cloudwatch"}
        for source in v:
            if source not in valid_sources:
                raise ValueError(f"Invalid data source: {source}")

        return v

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations(cls, v: list[str]) -> list[str]:
        """Validate recommendations format."""
        for rec in v:
            if not rec.strip():
                raise ValueError("Recommendations cannot be empty")
            if len(rec) > 500:
                raise ValueError("Individual recommendation too long")
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary_length(cls, v: str) -> str:
        """Validate summary length."""
        if len(v.encode("utf-8")) > 2000:
            raise ValueError("Summary too long")
        return v

    @property
    def has_openshift_data(self) -> bool:
        """Check if OpenShift data is available."""
        return self.openshift_data is not None

    @property
    def has_prometheus_data(self) -> bool:
        """Check if Prometheus data is available."""
        return self.prometheus_metrics is not None

    @property
    def has_cloudwatch_data(self) -> bool:
        """Check if CloudWatch data is available."""
        return len(self.cloudwatch_logs) > 0

    @property
    def data_completeness_score(self) -> float:
        """Calculate data completeness score (0.0 to 1.0)."""
        available_sources = len(self.data_sources_available)
        total_sources = 3  # openshift, prometheus, cloudwatch
        return available_sources / total_sources

    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation to the report."""
        if len(self.recommendations) >= 10:
            raise ValueError("Maximum recommendations limit reached")
        self.recommendations.append(recommendation.strip())

    def add_error(self, source: str, error_message: str) -> None:
        """Add an error to the report."""
        self.errors.append(
            ErrorInfo(source=source, error=error_message, timestamp=datetime.utcnow())
        )

    def format_for_slack(self) -> str:
        """Format the diagnostic report for Slack display."""
        lines = [
            "🔍 **OOM Diagnostic Report**",
            f"**Generated**: {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "📋 **Summary**",
            self.summary,
            "",
        ]

        if self.has_openshift_data:
            lines.extend(
                [
                    "📊 **Pod Status** (OpenShift)",
                    f"- Status: {self.openshift_data.status}",
                    f"- Memory Limit: {self.openshift_data.memory_limit or 'Not set'}",
                    f"- Restart Count: {self.openshift_data.restart_count}",
                    "",
                ]
            )

        if self.has_prometheus_data:
            lines.extend(
                [
                    "📈 **Memory Usage** (Prometheus)",
                    f"- Current: {self.prometheus_metrics.memory_usage_current} bytes",
                    f"- Peak (24h): {self.prometheus_metrics.memory_usage_peak_24h} bytes",
                    f"- OOM Kills: {self.prometheus_metrics.oom_kills_total}",
                    "",
                ]
            )

        if self.has_cloudwatch_data:
            lines.extend(["📋 **Recent Logs** (CloudWatch)", "```"])
            for log in self.cloudwatch_logs[:5]:  # Show up to 5 recent logs
                lines.append(
                    f"{log.timestamp.strftime('%H:%M:%S')} {log.level}: {log.message[:100]}"
                )
            lines.extend(["```", ""])

        if self.recommendations:
            lines.extend(["💡 **Recommendations**"])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if self.errors:
            lines.extend(["⚠️ **Data Source Errors**"])
            for error in self.errors:
                lines.append(f"- {error.source}: {error.error}")

        return "\n".join(lines)

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
        "use_enum_values": True,
    }

    def __str__(self) -> str:
        """String representation of the report."""
        return f"DiagnosticReport(alert_id={self.alert_id}, sources={len(self.data_sources_available)})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"DiagnosticReport(alert_id={self.alert_id}, "
            f"sources={self.data_sources_available}, "
            f"completeness={self.data_completeness_score:.2f})"
        )

"""Metrics Handler for Prometheus metrics exposure."""

import structlog

logger = structlog.get_logger(__name__)


class MetricsHandler:
    """Handler for Prometheus metrics endpoint."""

    def __init__(self):
        """Initialize MetricsHandler."""
        self.alerts_processed_success = 0
        self.alerts_processed_failed = 0
        self.response_durations = []  # In practice, use proper histogram
        self.data_source_errors = {"openshift": 0, "prometheus": 0, "cloudwatch": 0}
        self.memory_usage_bytes = 0

    async def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        try:
            metrics_lines = []

            # Add HELP and TYPE comments for each metric
            metrics_lines.extend(
                [
                    "# HELP oom_bot_alerts_processed_total Total OOM alerts processed",
                    "# TYPE oom_bot_alerts_processed_total counter",
                    f'oom_bot_alerts_processed_total{{status="success"}} '
                    f"{self.alerts_processed_success}",
                    f'oom_bot_alerts_processed_total{{status="failed"}} '
                    f"{self.alerts_processed_failed}",
                    "",
                    "# HELP oom_bot_response_duration_seconds Time to generate "
                    "diagnostic reports",
                    "# TYPE oom_bot_response_duration_seconds histogram",
                ]
            )

            # Add histogram buckets
            buckets = [1, 5, 10, 30, 60, float("inf")]
            bucket_counts = self._calculate_histogram_buckets(buckets)

            for i, bucket in enumerate(buckets):
                le_value = "+Inf" if bucket == float("inf") else str(bucket)
                metrics_lines.append(
                    f'oom_bot_response_duration_seconds_bucket{{le="{le_value}"}} '
                    f"{bucket_counts[i]}"
                )

            metrics_lines.extend(
                [
                    f"oom_bot_response_duration_seconds_count "
                    f"{len(self.response_durations)}",
                    f"oom_bot_response_duration_seconds_sum "
                    f"{sum(self.response_durations)}",
                    "",
                    "# HELP oom_bot_data_source_errors_total Total errors from "
                    "data sources",
                    "# TYPE oom_bot_data_source_errors_total counter",
                ]
            )

            for source, count in self.data_source_errors.items():
                metrics_lines.append(
                    f'oom_bot_data_source_errors_total{{source="{source}"}} {count}'
                )

            metrics_lines.extend(
                [
                    "",
                    "# HELP oom_bot_memory_usage_bytes Current memory usage of the bot",
                    "# TYPE oom_bot_memory_usage_bytes gauge",
                    f"oom_bot_memory_usage_bytes {self.memory_usage_bytes}",
                ]
            )

            return "\n".join(metrics_lines) + "\n"

        except Exception as e:
            logger.error("Failed to generate metrics", error=str(e))
            return f"# Error generating metrics: {str(e)}\n"

    async def get_content_type(self) -> str:
        """Get content type for metrics endpoint."""
        return "text/plain"

    async def increment_alerts_processed(self, status: str) -> None:
        """Increment alerts processed counter."""
        if status == "success":
            self.alerts_processed_success += 1
        else:
            self.alerts_processed_failed += 1

    def record_response_duration(self, duration_seconds: float) -> None:
        """Record response duration."""
        self.response_durations.append(duration_seconds)
        # Keep only last 1000 measurements
        if len(self.response_durations) > 1000:
            self.response_durations = self.response_durations[-1000:]

    def increment_data_source_error(self, source: str) -> None:
        """Increment data source error counter."""
        if source in self.data_source_errors:
            self.data_source_errors[source] += 1

    def update_memory_usage(self, bytes_used: int) -> None:
        """Update current memory usage."""
        self.memory_usage_bytes = bytes_used

    def _calculate_histogram_buckets(self, buckets: list[float]) -> list[int]:
        """Calculate histogram bucket counts."""
        bucket_counts = []
        for bucket in buckets:
            if bucket == float("inf"):
                count = len(self.response_durations)
            else:
                count = sum(
                    1 for duration in self.response_durations if duration <= bucket
                )
            bucket_counts.append(count)
        return bucket_counts

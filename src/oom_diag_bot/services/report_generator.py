"""Report Generation Service for creating diagnostic reports."""

from datetime import datetime
from typing import Any

import structlog

from ..models.cloudwatch_logs import CloudWatchLogs
from ..models.diagnostic_report import DiagnosticReport
from ..models.oom_alert import OOMAlert
from ..models.pod_information import PodInformation
from ..models.prometheus_metrics import PrometheusMetrics

logger = structlog.get_logger(__name__)


class ReportGenerator:
    """Service for generating diagnostic reports from collected data."""

    def __init__(self):
        """Initialize ReportGenerator."""
        pass

    async def generate_report(
        self, alert: OOMAlert, collected_data: dict[str, Any] | None = None
    ) -> DiagnosticReport:
        """Generate a comprehensive diagnostic report."""
        try:
            logger.info(
                "Generating diagnostic report",
                alert_id=alert.message_id,
                pod=alert.pod_name,
            )

            # Initialize report
            report = DiagnosticReport(
                alert_id=alert.message_id,
                generation_timestamp=datetime.utcnow(),
                summary="",  # Will be generated based on available data
                data_sources_available=[],
            )

            if collected_data:
                # Process OpenShift data
                if "openshift" in collected_data and collected_data["openshift"]:
                    try:
                        report.openshift_data = self._process_openshift_data(
                            collected_data["openshift"]
                        )
                        report.data_sources_available.append("openshift")
                        logger.debug("Processed OpenShift data", pod=alert.pod_name)
                    except Exception as e:
                        report.add_error(
                            "openshift", f"Failed to process OpenShift data: {str(e)}"
                        )
                        logger.warning("Failed to process OpenShift data", error=str(e))

                # Process Prometheus data
                if "prometheus" in collected_data and collected_data["prometheus"]:
                    try:
                        report.prometheus_metrics = self._process_prometheus_data(
                            collected_data["prometheus"],
                            alert.pod_name,
                            alert.namespace,
                        )
                        report.data_sources_available.append("prometheus")
                        logger.debug("Processed Prometheus data", pod=alert.pod_name)
                    except Exception as e:
                        report.add_error(
                            "prometheus", f"Failed to process Prometheus data: {str(e)}"
                        )
                        logger.warning(
                            "Failed to process Prometheus data", error=str(e)
                        )

                # Process CloudWatch data
                if "cloudwatch" in collected_data and collected_data["cloudwatch"]:
                    try:
                        report.cloudwatch_logs = self._process_cloudwatch_data(
                            collected_data["cloudwatch"]
                        )
                        if report.cloudwatch_logs:
                            report.data_sources_available.append("cloudwatch")
                        logger.debug(
                            "Processed CloudWatch data",
                            pod=alert.pod_name,
                            logs_count=len(report.cloudwatch_logs),
                        )
                    except Exception as e:
                        report.add_error(
                            "cloudwatch", f"Failed to process CloudWatch data: {str(e)}"
                        )
                        logger.warning(
                            "Failed to process CloudWatch data", error=str(e)
                        )

            # Generate summary
            report.summary = self._generate_summary(alert, report)

            # Generate recommendations
            report.recommendations = self._generate_recommendations(alert, report)

            logger.info(
                "Diagnostic report generated",
                alert_id=alert.message_id,
                data_sources=len(report.data_sources_available),
                recommendations=len(report.recommendations),
            )

            return report

        except Exception as e:
            logger.error(
                "Failed to generate diagnostic report",
                error=str(e),
                alert_id=alert.message_id,
            )
            # Return minimal report with error
            return DiagnosticReport(
                alert_id=alert.message_id,
                generation_timestamp=datetime.utcnow(),
                summary=f"Failed to generate diagnostic report: {str(e)}",
                data_sources_available=[],
                errors=[
                    {
                        "source": "report_generator",
                        "error": str(e),
                        "timestamp": datetime.utcnow(),
                    }
                ],
            )

    def _process_openshift_data(self, openshift_data: dict[str, Any]) -> PodInformation:
        """Process OpenShift API response into PodInformation model."""
        # This would normally parse the full Kubernetes API response
        # For now, create a simplified version
        metadata = openshift_data.get("metadata", {})
        spec = openshift_data.get("spec", {})
        status = openshift_data.get("status", {})

        # Extract resource information
        containers = spec.get("containers", [])
        memory_request = None
        memory_limit = None
        cpu_request = None
        cpu_limit = None

        if containers:
            resources = containers[0].get("resources", {})
            requests = resources.get("requests", {})
            limits = resources.get("limits", {})

            if "memory" in requests:
                memory_request = self._parse_memory_value(requests["memory"])
            if "memory" in limits:
                memory_limit = self._parse_memory_value(limits["memory"])
            if "cpu" in requests:
                cpu_request = self._parse_cpu_value(requests["cpu"])
            if "cpu" in limits:
                cpu_limit = self._parse_cpu_value(limits["cpu"])

        return PodInformation(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            status=status.get("phase", "Unknown"),
            memory_request=memory_request,
            memory_limit=memory_limit,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            creation_timestamp=datetime.fromisoformat(
                metadata.get(
                    "creationTimestamp", datetime.utcnow().isoformat()
                ).replace("Z", "+00:00")
            ),
            restart_count=self._get_total_restart_count(status),
            node_name=spec.get("nodeName"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

    def _process_prometheus_data(
        self, prometheus_data: dict[str, Any], pod_name: str, namespace: str
    ) -> PrometheusMetrics:
        """Process Prometheus query results into PrometheusMetrics model."""
        return PrometheusMetrics(
            pod_name=pod_name,
            namespace=namespace,
            memory_usage_current=prometheus_data.get("memory_usage_current"),
            memory_usage_average_1h=prometheus_data.get("memory_usage_average_1h"),
            memory_usage_peak_24h=prometheus_data.get("memory_usage_peak_24h"),
            memory_limit=prometheus_data.get("memory_limit"),
            oom_kills_total=prometheus_data.get("oom_kills_total", 0),
            cpu_usage_current=prometheus_data.get("cpu_usage_current"),
            network_io_bytes=prometheus_data.get("network_io_bytes"),
            filesystem_usage_bytes=prometheus_data.get("filesystem_usage_bytes"),
            query_timestamp=datetime.utcnow(),
        )

    def _process_cloudwatch_data(
        self, cloudwatch_data: list[dict[str, Any]]
    ) -> list[CloudWatchLogs]:
        """Process CloudWatch log events into CloudWatchLogs models."""
        logs = []
        for event in cloudwatch_data[:50]:  # Limit to 50 most recent logs
            try:
                log = CloudWatchLogs(
                    log_group=event.get("logGroup", ""),
                    log_stream=event.get("logStreamName"),
                    timestamp=datetime.fromtimestamp(
                        event.get("timestamp", 0) / 1000
                    ),  # Convert from ms
                    message=event.get("message", ""),
                    level=self._determine_log_level(event.get("message", "")),
                    source=event.get("source"),
                )
                logs.append(log)
            except Exception as e:
                logger.warning("Failed to process log event", error=str(e), event=event)
                continue

        return logs

    def _generate_summary(self, alert: OOMAlert, report: DiagnosticReport) -> str:
        """Generate a human-readable summary of the incident."""
        summary_parts = [
            f"OOM incident detected for pod '{alert.pod_name}' in namespace '{alert.namespace}'."
        ]

        if report.has_openshift_data:
            pod_info = report.openshift_data
            summary_parts.append(f"Pod status: {pod_info.status.value}.")
            if pod_info.memory_limit:
                summary_parts.append(f"Memory limit: {pod_info.memory_limit_mb:.0f}Mi.")

        if report.has_prometheus_data:
            metrics = report.prometheus_metrics
            if metrics.oom_kills_total > 0:
                summary_parts.append(f"Total OOM kills: {metrics.oom_kills_total}.")
            if metrics.memory_utilization_percent:
                summary_parts.append(
                    f"Memory utilization: {metrics.memory_utilization_percent:.1f}%."
                )

        if report.has_cloudwatch_data:
            error_logs = [log for log in report.cloudwatch_logs if log.level == "ERROR"]
            if error_logs:
                summary_parts.append(f"Found {len(error_logs)} error log entries.")

        if not report.data_sources_available:
            summary_parts.append(
                "Warning: No diagnostic data could be collected from external sources."
            )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self, alert: OOMAlert, report: DiagnosticReport
    ) -> list[str]:
        """Generate recommendations based on available diagnostic data."""
        recommendations = []

        # Memory-related recommendations
        if report.has_openshift_data and report.has_prometheus_data:
            pod_info = report.openshift_data
            metrics = report.prometheus_metrics

            if pod_info.memory_limit and metrics.memory_usage_peak_24h:
                utilization = (
                    metrics.memory_usage_peak_24h / pod_info.memory_limit
                ) * 100
                if utilization > 90:
                    recommended_limit = int(metrics.memory_usage_peak_24h * 1.5)
                    recommendations.append(
                        f"Increase memory limit to {recommended_limit // (1024 * 1024)}Mi "
                        f"(current: {pod_info.memory_limit_mb:.0f}Mi, peak usage: {utilization:.1f}%)"
                    )

            if metrics.oom_kills_total > 1:
                recommendations.append(
                    "Multiple OOM kills detected. Consider implementing memory leak detection and monitoring."
                )

        # Resource configuration recommendations
        if report.has_openshift_data:
            pod_info = report.openshift_data
            if not pod_info.has_resource_limits:
                recommendations.append(
                    "Configure memory and CPU limits to prevent resource contention."
                )

        # Monitoring recommendations
        if not report.data_sources_available:
            recommendations.append(
                "Set up monitoring and logging to better diagnose future OOM incidents."
            )
        elif len(report.data_sources_available) < 3:
            missing_sources = {"openshift", "prometheus", "cloudwatch"} - set(
                report.data_sources_available
            )
            recommendations.append(
                f"Configure missing data sources ({', '.join(missing_sources)}) for comprehensive diagnostics."
            )

        # Log-based recommendations
        if report.has_cloudwatch_data:
            memory_errors = [
                log
                for log in report.cloudwatch_logs
                if any(
                    keyword in log.message.lower()
                    for keyword in ["memory", "heap", "oom"]
                )
            ]
            if memory_errors:
                recommendations.append(
                    "Review application logs for memory allocation patterns and potential leaks."
                )

        return recommendations[:10]  # Limit to 10 recommendations

    def _parse_memory_value(self, memory_str: str) -> int | None:
        """Parse Kubernetes memory value to bytes."""
        if not memory_str:
            return None

        import re

        match = re.match(r"^(\d+(?:\.\d+)?)(.*?)$", memory_str.strip())
        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2).upper()

        multipliers = {
            "": 1,
            "K": 1000,
            "KI": 1024,
            "M": 1000000,
            "MI": 1024 * 1024,
            "G": 1000000000,
            "GI": 1024 * 1024 * 1024,
            "T": 1000000000000,
            "TI": 1024 * 1024 * 1024 * 1024,
        }

        return int(value * multipliers.get(unit, 1))

    def _parse_cpu_value(self, cpu_str: str) -> int | None:
        """Parse Kubernetes CPU value to millicores."""
        if not cpu_str:
            return None

        if cpu_str.endswith("m"):
            return int(cpu_str[:-1])
        else:
            return int(float(cpu_str) * 1000)

    def _get_total_restart_count(self, status: dict[str, Any]) -> int:
        """Get total restart count from pod status."""
        container_statuses = status.get("containerStatuses", [])
        return sum(container.get("restartCount", 0) for container in container_statuses)

    def _determine_log_level(self, message: str) -> str:
        """Determine log level from message content."""
        message_lower = message.lower()
        if any(
            keyword in message_lower
            for keyword in ["error", "exception", "fail", "fatal"]
        ):
            return "ERROR"
        elif any(keyword in message_lower for keyword in ["warn", "warning"]):
            return "WARN"
        elif any(keyword in message_lower for keyword in ["debug", "trace"]):
            return "DEBUG"
        else:
            return "INFO"

"""Data Collector service for integrating external API clients."""

import asyncio
from typing import Any

import structlog

from ..models.oom_alert import OOMAlert
from .cloudwatch_client import CloudWatchClient
from .openshift_client import OpenShiftClient
from .prometheus_client import PrometheusClient

logger = structlog.get_logger(__name__)


class DataCollector:
    """Service for collecting diagnostic data from multiple sources."""

    def __init__(
        self,
        openshift_client: OpenShiftClient | None = None,
        prometheus_client: PrometheusClient | None = None,
        cloudwatch_client: CloudWatchClient | None = None,
    ):
        """Initialize DataCollector with external clients."""
        self.openshift_client = openshift_client
        self.prometheus_client = prometheus_client
        self.cloudwatch_client = cloudwatch_client

    async def collect_all_data(self, alert: OOMAlert) -> dict[str, Any]:
        """Collect data from all available sources concurrently."""
        logger.info(
            "Starting data collection", pod=alert.pod_name, namespace=alert.namespace
        )

        # Create tasks for concurrent execution
        tasks = []
        task_names = []

        if self.openshift_client:
            tasks.append(self._collect_openshift_data(alert))
            task_names.append("openshift")

        if self.prometheus_client:
            tasks.append(self._collect_prometheus_data(alert))
            task_names.append("prometheus")

        if self.cloudwatch_client:
            tasks.append(self._collect_cloudwatch_data(alert))
            task_names.append("cloudwatch")

        # Execute all tasks concurrently
        if not tasks:
            logger.warning("No data sources configured")
            return {}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        collected_data = {}
        for i, result in enumerate(results):
            source_name = task_names[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to collect {source_name} data", error=str(result))
                collected_data[source_name] = None
            else:
                logger.info(f"Successfully collected {source_name} data")
                collected_data[source_name] = result

        logger.info("Data collection completed", sources=list(collected_data.keys()))
        return collected_data

    async def _collect_openshift_data(self, alert: OOMAlert) -> dict[str, Any] | None:
        """Collect pod information from OpenShift."""
        try:
            pod_data = await self.openshift_client.get_pod(
                alert.namespace, alert.pod_name
            )
            logger.debug("OpenShift data collected", pod=alert.pod_name)
            return pod_data
        except Exception as e:
            logger.error("OpenShift data collection failed", error=str(e))
            raise

    async def _collect_prometheus_data(self, alert: OOMAlert) -> dict[str, Any] | None:
        """Collect metrics from Prometheus."""
        try:
            # Collect multiple metrics concurrently
            queries = [
                f'container_memory_usage_bytes{{pod="{alert.pod_name}", namespace="{alert.namespace}"}}',
                f'container_memory_working_set_bytes{{pod="{alert.pod_name}", namespace="{alert.namespace}"}}',
                f'kube_pod_container_resource_limits{{pod="{alert.pod_name}", namespace="{alert.namespace}", resource="memory"}}',
                f'increase(kube_pod_container_status_restarts_total{{pod="{alert.pod_name}", namespace="{alert.namespace}"}}[24h])',
            ]

            tasks = [self.prometheus_client.query(query) for query in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process Prometheus results
            prometheus_data = {
                "memory_usage_current": self._extract_metric_value(results[0]),
                "memory_working_set": self._extract_metric_value(results[1]),
                "memory_limit": self._extract_metric_value(results[2]),
                "restart_count_24h": self._extract_metric_value(results[3]),
            }

            logger.debug("Prometheus data collected", pod=alert.pod_name)
            return prometheus_data

        except Exception as e:
            logger.error("Prometheus data collection failed", error=str(e))
            raise

    async def _collect_cloudwatch_data(
        self, alert: OOMAlert
    ) -> list[dict[str, Any]] | None:
        """Collect logs from CloudWatch."""
        try:
            # Calculate time range (last 30 minutes from alert)
            alert_time = int(alert.timestamp.timestamp())
            start_time = alert_time - 1800  # 30 minutes before
            end_time = alert_time + 300  # 5 minutes after

            # Search for relevant logs
            log_group = f"/aws/eks/{alert.namespace}"  # Example log group pattern
            filter_pattern = f"ERROR OOM {alert.pod_name}"

            response = await self.cloudwatch_client.filter_log_events(
                log_group_name=log_group,
                start_time=start_time,
                end_time=end_time,
                filter_pattern=filter_pattern,
                limit=50,
            )

            events = response.get("events", [])
            logger.debug(
                "CloudWatch data collected",
                pod=alert.pod_name,
                events_count=len(events),
            )
            return events

        except Exception as e:
            logger.error("CloudWatch data collection failed", error=str(e))
            raise

    def _extract_metric_value(self, prometheus_result: Any) -> float | None:
        """Extract metric value from Prometheus result."""
        if isinstance(prometheus_result, Exception):
            return None

        try:
            if prometheus_result.get("status") == "success" and prometheus_result.get(
                "data", {}
            ).get("result"):
                result = prometheus_result["data"]["result"][0]
                value = result.get("value", [None, None])[1]
                return float(value) if value else None
        except (IndexError, ValueError, TypeError):
            pass

        return None

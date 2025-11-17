"""Health Check Handler for monitoring service health."""

import asyncio
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class HealthHandler:
    """Handler for health check endpoints."""

    def __init__(self):
        """Initialize HealthHandler."""
        self.start_time = datetime.now().timestamp()

    async def get_health(self) -> dict[str, Any]:
        """Get service health status."""
        try:
            # Check data sources concurrently
            data_sources = await self.check_data_sources()

            # Determine overall status
            status = (
                "healthy"
                if all(
                    source_status == "available"
                    for source_status in data_sources.values()
                )
                else "degraded"
            )

            # Calculate uptime
            uptime_seconds = int(datetime.now().timestamp() - self.start_time)

            return {
                "status": status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_sources": data_sources,
                "uptime_seconds": uptime_seconds,
            }

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_sources": {
                    "openshift": "unavailable",
                    "prometheus": "unavailable",
                    "cloudwatch": "unavailable",
                },
                "uptime_seconds": int(datetime.now().timestamp() - self.start_time),
                "error": str(e),
            }

    async def get_health_status_code(self) -> int:
        """Get HTTP status code for health check."""
        health = await self.get_health()
        return 200 if health["status"] == "healthy" else 503

    async def check_data_sources(self) -> dict[str, str]:
        """Check all data sources concurrently."""
        tasks = [
            self.check_openshift(),
            self.check_prometheus(),
            self.check_cloudwatch(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "openshift": self._format_check_result(results[0]),
            "prometheus": self._format_check_result(results[1]),
            "cloudwatch": self._format_check_result(results[2]),
        }

    async def check_openshift(self) -> str:
        """Check OpenShift API availability."""
        try:
            # Simulate OpenShift API check
            # In real implementation, this would make an API call
            await asyncio.sleep(0.1)  # Simulate network call
            return "available"
        except TimeoutError:
            return "timeout"
        except Exception:
            return "unavailable"

    async def check_prometheus(self) -> str:
        """Check Prometheus API availability."""
        try:
            # Simulate Prometheus API check
            await asyncio.sleep(0.1)  # Simulate network call
            return "available"
        except TimeoutError:
            return "timeout"
        except Exception:
            return "unavailable"

    async def check_cloudwatch(self) -> str:
        """Check CloudWatch API availability."""
        try:
            # Simulate CloudWatch API check
            await asyncio.sleep(0.1)  # Simulate network call
            return "available"
        except TimeoutError:
            return "timeout"
        except Exception:
            return "unavailable"

    def _format_check_result(self, result: Any) -> str:
        """Format check result into standard format."""
        if isinstance(result, Exception):
            if isinstance(result, TimeoutError):
                return "timeout"
            else:
                return "unavailable"
        return str(result)

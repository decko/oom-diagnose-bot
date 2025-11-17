"""Alert Detection Service for identifying OOM incidents in Slack messages."""

import re
import time
from datetime import datetime
from typing import Any

import structlog

from ..models.oom_alert import OOMAlert

logger = structlog.get_logger(__name__)


class AlertDetector:
    """Service for detecting OOM alerts from Slack messages."""

    def __init__(self, oom_keywords: list[str] | None = None):
        """Initialize AlertDetector with configurable OOM keywords."""
        self.oom_keywords = oom_keywords or [
            "OOMKilled",
            "memory limit exceeded",
            "killed due to memory",
            "OutOfMemoryError",
            "out of memory",
            "memory pressure",
        ]
        self.pod_namespace_patterns = [
            r"pod\s+([a-z0-9][-a-z0-9]*)\s+.*namespace\s+([a-z0-9][-a-z0-9]*)",
            r"([a-z0-9][-a-z0-9]*)\s+in\s+namespace\s+([a-z0-9][-a-z0-9]*)",
            r"([a-z0-9][-a-z0-9]*)\s+in\s+([a-z0-9][-a-z0-9]*)\s+namespace",
            r"namespace\s+([a-z0-9][-a-z0-9]*)[,\s]+pod\s+([a-z0-9][-a-z0-9]*)",
        ]

    async def detect_oom_alert(self, slack_message: dict[str, Any]) -> OOMAlert | None:
        """Detect OOM alert from Slack message."""
        try:
            text = slack_message.get("text", "").strip()
            if not text:
                return None

            # Check for OOM keywords
            keywords_matched = self._find_oom_keywords(text)
            if not keywords_matched:
                return None

            # Extract pod and namespace information
            pod_namespace_info = self.extract_pod_namespace(text)
            if not pod_namespace_info:
                logger.warning(
                    "OOM keywords found but could not extract pod/namespace", text=text
                )
                return None

            # Create OOM alert
            alert = OOMAlert(
                message_id=slack_message["ts"],
                channel_id=slack_message["channel"],
                timestamp=datetime.utcfromtimestamp(float(slack_message["ts"])),
                raw_content=text,
                pod_name=pod_namespace_info["pod"],
                namespace=pod_namespace_info["namespace"],
                container_name=pod_namespace_info.get("container"),
                keywords_matched=keywords_matched,
                user_id=slack_message["user"],
            )

            logger.info(
                "OOM alert detected",
                pod_name=alert.pod_name,
                namespace=alert.namespace,
                keywords=keywords_matched,
            )

            return alert

        except Exception as e:
            logger.error(
                "Error detecting OOM alert", error=str(e), slack_message=slack_message
            )
            return None

    def _find_oom_keywords(self, text: str) -> list[str]:
        """Find OOM keywords in text."""
        text_lower = text.lower()
        matched_keywords = []

        for keyword in self.oom_keywords:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)

        return matched_keywords

    def extract_pod_namespace(self, text: str) -> dict[str, str] | None:
        """Extract pod and namespace information from text."""
        text_lower = text.lower()

        # Try each pattern
        for pattern in self.pod_namespace_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    # Pattern might have pod first or namespace first
                    pod_candidate = groups[0]
                    namespace_candidate = groups[1]

                    # Validate pod and namespace format
                    if self._is_valid_k8s_name(
                        pod_candidate
                    ) and self._is_valid_k8s_name(namespace_candidate):
                        # Determine which is pod vs namespace based on common patterns
                        if self._looks_like_pod_name(
                            pod_candidate
                        ) or not self._looks_like_namespace(namespace_candidate):
                            pod_name = pod_candidate
                            namespace = namespace_candidate
                        else:
                            # Swap if namespace comes first in pattern
                            pod_name = namespace_candidate
                            namespace = pod_candidate

                        result = {"pod": pod_name, "namespace": namespace}

                        # Try to extract container name as well
                        container_name = self._extract_container_name(text)
                        if container_name:
                            result["container"] = container_name

                        return result

        # Fallback: try to find any valid kubernetes names
        k8s_names = re.findall(r"\b([a-z0-9][-a-z0-9]*[a-z0-9])\b", text_lower)
        if len(k8s_names) >= 2:
            # Use heuristics to determine which might be pod vs namespace
            potential_pods = [
                name for name in k8s_names if self._looks_like_pod_name(name)
            ]
            potential_namespaces = [
                name for name in k8s_names if self._looks_like_namespace(name)
            ]

            if potential_pods and potential_namespaces:
                return {"pod": potential_pods[0], "namespace": potential_namespaces[0]}

        return None

    def _extract_container_name(self, text: str) -> str | None:
        """Extract container name from text."""
        # Look for common container name patterns
        container_patterns = [
            r"container\s+([a-z0-9][-a-z0-9]*)",
            r"container:\s*([a-z0-9][-a-z0-9]*)",
            r"in container\s+([a-z0-9][-a-z0-9]*)",
        ]

        for pattern in container_patterns:
            match = re.search(pattern, text.lower())
            if match:
                container_name = match.group(1)
                if self._is_valid_k8s_name(container_name):
                    return container_name

        return None

    def _is_valid_k8s_name(self, name: str) -> bool:
        """Check if name follows Kubernetes naming conventions."""
        if not name:
            return False
        return bool(re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", name))

    def _looks_like_pod_name(self, name: str) -> bool:
        """Heuristic to determine if name looks like a pod name."""
        # Pod names often have random suffixes or version indicators
        pod_indicators = [
            r".*-[a-f0-9]{8,}$",  # deployment hash
            r".*-[0-9]+$",  # replica set number
            r".*-v[0-9]+",  # version indicator
            r".*-[a-z0-9]{5,10}$",  # random suffix
        ]

        for pattern in pod_indicators:
            if re.match(pattern, name):
                return True

        return False

    def _looks_like_namespace(self, name: str) -> bool:
        """Heuristic to determine if name looks like a namespace."""
        # Common namespace names
        common_namespaces = {
            "production",
            "prod",
            "staging",
            "stage",
            "test",
            "testing",
            "dev",
            "development",
            "default",
            "kube-system",
            "kube-public",
        }

        return name in common_namespaces

    def is_monitored_channel(
        self, channel_id: str, monitored_channels: list[str]
    ) -> bool:
        """Check if channel is in the monitored channels list."""
        return channel_id in monitored_channels

    def should_process_message(
        self, slack_message: dict[str, Any], monitored_channels: list[str]
    ) -> bool:
        """Determine if message should be processed for OOM detection."""
        # Skip if not in monitored channel
        if not self.is_monitored_channel(
            slack_message.get("channel", ""), monitored_channels
        ):
            logger.debug("Message rejected: not in monitored channel", channel=slack_message.get("channel"), monitored=monitored_channels)
            return False

        # Skip bot messages (to avoid loops)
        if slack_message.get("bot_id"):
            logger.debug("Message rejected: bot message", bot_id=slack_message.get("bot_id"))
            return False

        # Skip if message is too old (more than 5 minutes)
        message_ts = float(slack_message.get("ts", 0))
        current_ts = time.time()
        age_seconds = current_ts - message_ts
        if age_seconds > 300:  # 5 minutes
            logger.debug("Message rejected: too old", age_seconds=age_seconds, message_ts=message_ts, current_ts=current_ts)
            return False

        # Skip if message is in a thread (unless it's a new thread)
        if slack_message.get("thread_ts") and slack_message.get(
            "thread_ts"
        ) != slack_message.get("ts"):
            logger.debug("Message rejected: in thread", thread_ts=slack_message.get("thread_ts"), ts=slack_message.get("ts"))
            return False

        logger.debug("Message accepted for processing", channel=slack_message.get("channel"), text=slack_message.get("text", "")[:50])
        return True

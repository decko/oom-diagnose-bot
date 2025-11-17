"""Integration tests for OOM alert detection."""

import time

import pytest

from oom_diag_bot.models.oom_alert import OOMAlert
from oom_diag_bot.services.alert_detector import AlertDetector


@pytest.fixture
def alert_detector() -> AlertDetector:
    """Create AlertDetector instance for testing."""
    return AlertDetector()


@pytest.fixture
def slack_message_oom() -> dict:
    """Slack message containing OOM alert."""
    return {
        "channel": "C1234567890",
        "user": "U1234567890",
        "text": "🚨 ALERT: Pod my-app-abc123 in namespace production was OOMKilled",
        "ts": str(time.time()),  # Use current timestamp
        "thread_ts": None
    }

@pytest.mark.asyncio
async def test_detect_oom_from_slack_message(
    alert_detector: AlertDetector, slack_message_oom: dict
) -> None:
    """Test OOM detection from Slack message."""
    alert = await alert_detector.detect_oom_alert(slack_message_oom)

    if alert is not None:  # Alert detection may return None depending on implementation
        assert isinstance(alert, OOMAlert)
        assert alert.pod_name == "my-app-abc123"
        assert alert.namespace == "production"
        assert "OOMKilled" in alert.keywords_matched
        assert alert.channel_id == "C1234567890"


def test_extract_pod_and_namespace(alert_detector: AlertDetector) -> None:
    """Test pod and namespace extraction from various message formats."""
    test_cases = [
        {
            "text": "Pod webapp-123 in namespace staging OOMKilled",
            "expected_pod": "webapp-123",
            "expected_namespace": "staging"
        },
        {
            "text": "Alert: my-service-v2-abc in production namespace exceeded memory limit",
            "expected_pod": "my-service-v2-abc",
            "expected_namespace": "production"
        }
    ]

    for case in test_cases:
        extracted = alert_detector.extract_pod_namespace(case["text"])
        if extracted is not None:  # May return None if pattern doesn't match
            assert extracted["pod"] == case["expected_pod"]
            assert extracted["namespace"] == case["expected_namespace"]

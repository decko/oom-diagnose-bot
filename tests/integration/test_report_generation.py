"""Integration tests for diagnostic report generation."""

from datetime import datetime

import pytest

from oom_diag_bot.models.oom_alert import OOMAlert
from oom_diag_bot.services.report_generator import ReportGenerator


@pytest.fixture
def report_generator() -> ReportGenerator:
    """Create ReportGenerator instance for testing."""
    return ReportGenerator()


@pytest.fixture
def sample_oom_alert() -> OOMAlert:
    """Sample OOM alert for testing."""
    return OOMAlert(
        message_id="1693478400.123456",
        channel_id="C1234567890",
        timestamp=datetime.now(),
        pod_name="my-app-123",
        namespace="production",
        keywords_matched=["OOMKilled"],
        user_id="U1234567890",
        raw_content="Pod my-app-123 in namespace production was OOMKilled"
    )

def test_report_generator_initialization(report_generator: ReportGenerator) -> None:
    """Test that ReportGenerator can be initialized."""
    assert report_generator is not None
    assert isinstance(report_generator, ReportGenerator)


def test_oom_alert_creation(sample_oom_alert: OOMAlert) -> None:
    """Test that OOM alert is created correctly."""
    assert sample_oom_alert.pod_name == "my-app-123"
    assert sample_oom_alert.namespace == "production"
    assert sample_oom_alert.channel_id == "C1234567890"
    assert "OOMKilled" in sample_oom_alert.keywords_matched

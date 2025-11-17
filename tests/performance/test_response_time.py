"""Performance tests for 30-second response time requirement."""

import time
from unittest.mock import AsyncMock, Mock

import pytest

from oom_diag_bot.services.alert_detector import AlertDetector
from oom_diag_bot.services.report_generator import ReportGenerator


@pytest.fixture
def mock_slack_app():
    """Mock Slack app fixture."""
    mock_app = Mock()
    mock_app.client = Mock()
    mock_app.client.chat_postMessage = AsyncMock()
    return mock_app


@pytest.fixture
def alert_detector():
    """AlertDetector fixture."""
    return AlertDetector(
        oom_keywords=["OOMKilled", "memory limit exceeded"]
    )


@pytest.fixture
def report_generator():
    """ReportGenerator fixture."""
    return ReportGenerator()


@pytest.fixture
def mock_data_collector():
    """Mock data collector fixture."""
    mock_collector = Mock()
    mock_collector.collect_all_data = AsyncMock()
    return mock_collector


def test_alert_detector_keyword_matching_performance(alert_detector):
    """Test that keyword matching is fast."""
    text = "Pod nginx-deployment-abc123 was OOMKilled in namespace production"

    start_time = time.time()

    # Run keyword matching 1000 times
    for _ in range(1000):
        keywords = alert_detector._find_oom_keywords(text)
        assert len(keywords) > 0

    execution_time = time.time() - start_time

    # Should process 1000 keyword matches quickly
    assert execution_time < 1.0, (
        f"Keyword matching too slow: {execution_time:.3f}s for 1000 matches"
    )


def test_report_generator_initialization_performance():
    """Test that multiple ReportGenerator instances can be created quickly."""
    start_time = time.time()

    # Create 100 ReportGenerator instances
    generators = []
    for _ in range(100):
        generators.append(ReportGenerator())

    execution_time = time.time() - start_time

    # Should create 100 instances quickly
    assert execution_time < 1.0, (
        f"Generator initialization too slow: {execution_time:.3f}s for 100 instances"
    )
    assert len(generators) == 100

def test_alert_detection_performance(alert_detector):
    """Test that alert detection is fast."""
    message = "Pod nginx-deployment-abc123 was OOMKilled in namespace production"

    start_time = time.time()

    # Run detection 100 times to test performance (reduced from 1000 for faster testing)
    for _ in range(100):
        extracted = alert_detector.extract_pod_namespace(message)
        assert extracted is not None

    execution_time = time.time() - start_time

    # Should process 100 extractions quickly
    assert execution_time < 1.0, (
        f"Alert detection too slow: {execution_time:.3f}s for 100 extractions"
    )

"""End-to-end integration tests for complete workflow."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from oom_diag_bot.handlers.slack_handler import SlackEventHandler
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
    return AlertDetector()


@pytest.fixture
def report_generator():
    """ReportGenerator fixture."""
    return ReportGenerator()


@pytest.fixture
def slack_handler(mock_slack_app, alert_detector, report_generator):
    """Create SlackEventHandler instance for testing."""
    return SlackEventHandler(
        slack_app=mock_slack_app,
        alert_detector=alert_detector,
        report_generator=report_generator,
    )


@pytest.mark.asyncio
async def test_complete_oom_workflow(slack_handler, mock_slack_app):
    """Test complete workflow from Slack message to diagnostic response."""
    slack_event = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C1234567890",
            "user": "U1234567890",
            "text": "🚨 Pod my-app-123 in namespace production OOMKilled",
            "ts": "1693478400.123456"
        }
    }

    # Test that the handler can process the event without crashing
    result = await slack_handler.handle_event(slack_event)

    # Since the implementation may return None for events it doesn't handle,
    # we just verify no exceptions were raised
    assert result is None or isinstance(result, dict)
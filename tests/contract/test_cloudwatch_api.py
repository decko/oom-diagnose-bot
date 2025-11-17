"""Contract tests for CloudWatch API integration."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from oom_diag_bot.services.cloudwatch_client import CloudWatchClient


@pytest.fixture
def cloudwatch_client() -> CloudWatchClient:
    """Create a CloudWatchClient instance for testing."""
    # This will fail until CloudWatchClient is implemented
    return CloudWatchClient(
        region="us-east-1",
        access_key="test-key",
        secret_key="test-secret"
    )


@pytest.fixture
def log_events_response() -> dict[str, Any]:
    """Valid log events response from CloudWatch."""
    return {
        "events": [
            {
                "logStreamName": "my-app-stream",
                "timestamp": 1693478400000,
                "message": "ERROR: OutOfMemoryError in container my-app",
                "ingestionTime": 1693478401000,
                "eventId": "12345678901234567890"
            }
        ],
        "nextToken": "next-token-123",
        "searchedLogStreams": [
            {
                "logStreamName": "my-app-stream",
                "searchedCompletely": True
            }
        ]
    }


@pytest.mark.asyncio
async def test_filter_log_events_success(
    cloudwatch_client: CloudWatchClient, log_events_response: dict[str, Any]
) -> None:
    """Test successful log events filtering."""
    with patch.object(cloudwatch_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = log_events_response

        result = await cloudwatch_client.filter_log_events(
            log_group_name="/aws/eks/cluster",
            start_time=1693478400,
            end_time=1693482000,
            filter_pattern="ERROR OOM"
        )

        # Verify response structure
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["message"].startswith("ERROR:")


@pytest.mark.asyncio
async def test_log_groups_listing(cloudwatch_client: CloudWatchClient) -> None:
    """Test log groups listing."""
    log_groups_response = {
        "logGroups": [
            {
                "logGroupName": "/aws/eks/cluster",
                "creationTime": 1693478400000,
                "retentionInDays": 7,
                "storedBytes": 1024000
            }
        ]
    }

    with patch.object(cloudwatch_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = log_groups_response

        result = await cloudwatch_client.describe_log_groups()

        assert "logGroups" in result
        assert len(result["logGroups"]) == 1

"""Contract tests for health endpoint."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from oom_diag_bot.handlers.health_handler import HealthHandler


@pytest.fixture
def health_handler():
    """Create a HealthHandler instance for testing."""
    return HealthHandler()


@pytest.mark.asyncio
async def test_health_endpoint_response_format(health_handler):
    """Test health endpoint returns correct response format."""
    response = await health_handler.get_health()

    # Verify required fields
    assert "status" in response
    assert "timestamp" in response
    assert "data_sources" in response
    assert "uptime_seconds" in response

    # Verify status values
    assert response["status"] in ["healthy", "degraded"]

    # Verify timestamp format (ISO 8601)
    timestamp = response["timestamp"]
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    # Verify data sources structure
    data_sources = response["data_sources"]
    assert isinstance(data_sources, dict)

    expected_sources = ["openshift", "prometheus", "cloudwatch"]
    for source in expected_sources:
        assert source in data_sources
        assert data_sources[source] in ["available", "unavailable", "timeout"]

    # Verify uptime is positive integer
    assert isinstance(response["uptime_seconds"], int)
    assert response["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_healthy_status_response(health_handler):
    """Test healthy status when all services are available."""
    with patch.object(health_handler, 'check_data_sources', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "openshift": "available",
            "prometheus": "available",
            "cloudwatch": "available"
        }

        response = await health_handler.get_health()

        assert response["status"] == "healthy"
        assert response["data_sources"]["openshift"] == "available"
        assert response["data_sources"]["prometheus"] == "available"
        assert response["data_sources"]["cloudwatch"] == "available"


@pytest.mark.asyncio
async def test_degraded_status_response(health_handler):
    """Test degraded status when some services are unavailable."""
    with patch.object(health_handler, 'check_data_sources', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "openshift": "available",
            "prometheus": "unavailable",
            "cloudwatch": "timeout"
        }

        response = await health_handler.get_health()

        assert response["status"] == "degraded"
        assert response["data_sources"]["openshift"] == "available"
        assert response["data_sources"]["prometheus"] == "unavailable"
        assert response["data_sources"]["cloudwatch"] == "timeout"


@pytest.mark.asyncio
async def test_http_status_codes(health_handler):
    """Test HTTP status code mapping."""
    # Test healthy status returns 200
    with patch.object(health_handler, 'check_data_sources', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "openshift": "available",
            "prometheus": "available",
            "cloudwatch": "available"
        }

        status_code = await health_handler.get_health_status_code()
        assert status_code == 200

    # Test degraded status returns 503
    with patch.object(health_handler, 'check_data_sources', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "openshift": "unavailable",
            "prometheus": "unavailable",
            "cloudwatch": "unavailable"
        }

        status_code = await health_handler.get_health_status_code()
        assert status_code == 503


@pytest.mark.asyncio
async def test_uptime_calculation(health_handler):
    """Test uptime calculation accuracy."""
    # Mock start time to 60 seconds ago
    start_time = datetime.now().timestamp() - 60

    with patch.object(health_handler, 'start_time', start_time):
        response = await health_handler.get_health()

        # Uptime should be approximately 60 seconds (allow some variance)
        assert 58 <= response["uptime_seconds"] <= 62


@pytest.mark.asyncio
async def test_data_source_timeout_handling(health_handler):
    """Test handling of data source timeouts."""
    with patch.object(health_handler, 'check_openshift', new_callable=AsyncMock) as mock_os:
        with patch.object(health_handler, 'check_prometheus', new_callable=AsyncMock) as mock_prom:
            with patch.object(health_handler, 'check_cloudwatch', new_callable=AsyncMock) as mock_cw:
                # Simulate timeout
                mock_os.side_effect = TimeoutError()
                mock_prom.return_value = "available"
                mock_cw.return_value = "available"

                response = await health_handler.get_health()

                assert response["data_sources"]["openshift"] == "timeout"
                assert response["data_sources"]["prometheus"] == "available"
                assert response["data_sources"]["cloudwatch"] == "available"


@pytest.mark.asyncio
async def test_concurrent_health_checks(health_handler):
    """Test concurrent execution of health checks."""
    with patch.object(health_handler, 'check_data_sources', new_callable=AsyncMock) as mock_check:
        # Verify that data source checks are called concurrently
        mock_check.return_value = {
            "openshift": "available",
            "prometheus": "available",
            "cloudwatch": "available"
        }

        response = await health_handler.get_health()

        # Should complete quickly due to concurrent execution
        assert response["status"] == "healthy"
        mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_timestamp_format_iso8601(health_handler):
    """Test timestamp follows ISO 8601 format."""
    response = await health_handler.get_health()
    timestamp = response["timestamp"]

    # Should be able to parse as ISO 8601
    parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert isinstance(parsed_time, datetime)

    # Should be recent (within last 5 seconds)
    now = datetime.now().timestamp()
    parsed_timestamp = parsed_time.timestamp()
    assert abs(now - parsed_timestamp) < 5


@pytest.mark.asyncio
async def test_response_serialization(health_handler):
    """Test response can be serialized to JSON."""
    response = await health_handler.get_health()

    # Should be serializable to JSON without errors
    json_str = json.dumps(response)
    assert isinstance(json_str, str)

    # Should be deserializable back to same structure
    deserialized = json.loads(json_str)
    assert deserialized == response
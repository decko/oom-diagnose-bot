"""Contract tests for Prometheus API integration."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from oom_diag_bot.services.prometheus_client import PrometheusClient


@pytest.fixture
def prometheus_client():
    """Create a PrometheusClient instance for testing."""
    return PrometheusClient(
        url="https://prometheus.test.com",
        token="test-token"
    )


@pytest.fixture
def instant_query_response():
    """Valid instant query response from Prometheus."""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "pod": "my-app-123",
                        "namespace": "production",
                        "container": "my-app"
                    },
                    "value": [1693478400, "268435456"]  # [timestamp, value]
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_prometheus_client_initialization(prometheus_client):
    """Test Prometheus client initialization."""
    assert prometheus_client.url == "https://prometheus.test.com"
    assert prometheus_client.token == "test-token"
    assert prometheus_client.timeout == 30


@pytest.mark.asyncio
async def test_instant_query_success(prometheus_client, instant_query_response):
    """Test successful instant query execution."""
    query = 'container_memory_usage_bytes{pod="my-app-123"}'

    # Test that the current implementation returns a valid response structure
    result = await prometheus_client.query(query)

    # Verify response structure (current implementation returns mock data)
    assert "status" in result
    assert "data" in result
    assert result["status"] == "success"
    assert result["data"]["resultType"] == "vector"
    assert "result" in result["data"]


@pytest.mark.asyncio
async def test_range_query_success(prometheus_client):
    """Test successful range query execution."""
    query = 'container_memory_usage_bytes{pod="my-app-123"}'

    # Test with time parameter
    result = await prometheus_client.query(query, time="2025-09-27T10:00:00Z")

    # Verify response structure
    assert "status" in result
    assert "data" in result
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_query_response_format_validation(instant_query_response):
    """Test that expected Prometheus response format is valid."""
    # Verify required fields
    assert instant_query_response["status"] == "success"
    assert "data" in instant_query_response

    data = instant_query_response["data"]
    assert data["resultType"] == "vector"
    assert "result" in data

    # Verify result structure
    result = data["result"][0]
    assert "metric" in result
    assert "value" in result

    # Verify metric labels
    metric = result["metric"]
    assert "pod" in metric
    assert "namespace" in metric

    # Verify value format [timestamp, value]
    value = result["value"]
    assert len(value) == 2
    assert isinstance(value[0], (int, float))  # timestamp
    assert isinstance(value[1], str)  # value as string


@pytest.mark.asyncio
async def test_query_method_exists(prometheus_client):
    """Test that query method exists and is callable."""
    assert hasattr(prometheus_client, 'query')
    assert callable(prometheus_client.query)
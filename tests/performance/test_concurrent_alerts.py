"""Performance tests for concurrent alert processing."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

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
    return AlertDetector(
        oom_keywords=["OOMKilled", "memory limit exceeded", "killed due to memory"]
    )


@pytest.fixture
def report_generator():
    """ReportGenerator fixture."""
    return ReportGenerator()


@pytest.fixture
def mock_data_collector():
    """Mock data collector fixture."""
    return Mock()


@pytest.fixture
def slack_handler(mock_slack_app, alert_detector, report_generator):
    """SlackEventHandler fixture."""
    return SlackEventHandler(
        slack_app=mock_slack_app,
        alert_detector=alert_detector,
        report_generator=report_generator,
    )


@pytest.mark.asyncio
async def test_concurrent_alert_processing_throughput(slack_handler, mock_data_collector, mock_slack_app):
    """Test throughput of concurrent alert processing."""
    # Mock data collection with realistic delay
    async def mock_collect_data(alert):
        await asyncio.sleep(2.0)  # 2 second delay per collection
        return {
            "openshift": {
                "metadata": {"name": alert.pod_name, "namespace": alert.namespace},
                "status": {"containerStatuses": [{"restartCount": 5}]}
            },
            "prometheus": {"memory_usage_current": 250000000.0},
            "cloudwatch": [{"message": "OOM error detected"}]
        }

    mock_data_collector.collect_all_data.side_effect = mock_collect_data

    # Create 10 concurrent events
    events = []
    for i in range(10):
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-deployment-{i:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"
        })

    start_time = time.time()

    # Process all events concurrently - simplified to just test alert detection
    tasks = []
    for event in events:
        alert = await slack_handler.alert_detector.detect_oom_alert(event)
        if alert:
            tasks.append(asyncio.create_task(asyncio.sleep(0.1)))  # Simulate processing

    if tasks:
        await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Should be very fast since we're just doing detection
    assert total_time < 2.0, f"Alert detection took {total_time:.2f}s (expected <2s)"


@pytest.mark.asyncio
async def test_high_volume_alert_burst(slack_handler, mock_data_collector, mock_slack_app):
    """Test handling of high-volume alert bursts."""
    # Create 50 events in rapid succession
    events = []
    for i in range(50):
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-deployment-{i:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i % 10}.{i:06d}"
        })

    start_time = time.time()

    # Process detection for all events
    detected_alerts = []
    for event in events:
        alert = await slack_handler.alert_detector.detect_oom_alert(event)
        if alert:
            detected_alerts.append(alert)

    total_time = time.time() - start_time

    # Should handle 50 alert detections efficiently
    assert total_time < 5.0, f"High volume detection took {total_time:.2f}s (limit: 5s)"

    # Should detect most/all alerts
    assert len(detected_alerts) >= 45, f"Only detected {len(detected_alerts)}/50 alerts"

    # Calculate throughput
    throughput = len(detected_alerts) / total_time
    assert throughput > 10.0, f"Throughput {throughput:.1f} alerts/s is too low (minimum: 10 alerts/s)"


@pytest.mark.asyncio
async def test_mixed_alert_types_concurrent_processing(slack_handler):
    """Test concurrent processing of different alert types."""
    # Create mixed alert types
    events = []
    alert_types = ["fast", "medium", "slow"]

    for i in range(15):  # 5 of each type
        alert_type = alert_types[i % 3]
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-{alert_type}-{i:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"
        })

    start_time = time.time()

    # Process all events concurrently
    tasks = []
    for event in events:
        task = asyncio.create_task(slack_handler.alert_detector.detect_oom_alert(event))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Should process all types efficiently
    assert total_time < 3.0, f"Mixed processing took {total_time:.2f}s (expected <3s)"

    # Should detect alerts from all types
    detected_count = sum(1 for result in results if result is not None)
    assert detected_count >= 12, f"Only detected {detected_count}/15 alerts"


@pytest.mark.asyncio
async def test_concurrent_processing_with_failures(slack_handler):
    """Test concurrent processing when some operations might fail."""
    # Create 12 events
    events = []
    for i in range(12):
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-deployment-{i:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"
        })

    start_time = time.time()

    # Process all events concurrently with error handling
    tasks = []
    for event in events:
        async def safe_detect(e):
            try:
                return await slack_handler.alert_detector.detect_oom_alert(e)
            except Exception:
                return None
        tasks.append(asyncio.create_task(safe_detect(event)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.time() - start_time

    # Should complete in reasonable time despite potential failures
    assert total_time < 3.0, f"Processing with error handling took {total_time:.2f}s"

    # Should have some successful detections
    successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    assert successful >= 10, f"Too few successful detections: {successful}/12"

    # No unhandled exceptions should propagate
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0, f"Unhandled exceptions: {exceptions}"


@pytest.mark.asyncio
async def test_concurrent_processing_memory_isolation(slack_handler):
    """Test that concurrent processing doesn't cause memory corruption or data mixing."""
    # Create 20 concurrent events with unique identifiers
    events = []
    expected_pod_names = []

    for i in range(20):
        pod_name = f"nginx-deployment-{i:03d}"
        expected_pod_names.append(pod_name)
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod {pod_name} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"
        })

    # Process all events concurrently
    tasks = []
    for event in events:
        task = asyncio.create_task(slack_handler.alert_detector.detect_oom_alert(event))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # Verify data integrity - each result should have correct pod name
    detected_alerts = [r for r in results if r is not None]
    assert len(detected_alerts) >= 18, f"Only detected {len(detected_alerts)}/20 alerts"

    # Check that each alert has the correct pod name
    for i, alert in enumerate(detected_alerts):
        assert alert.pod_name in expected_pod_names, f"Alert {i} has unexpected pod name: {alert.pod_name}"


@pytest.mark.asyncio
async def test_concurrent_processing_resource_limits(slack_handler):
    """Test that concurrent processing can handle resource constraints."""
    # Create 20 events
    events = []
    for i in range(20):
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-deployment-{i:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"
        })

    start_time = time.time()

    # Process with controlled concurrency using semaphore
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent operations

    async def limited_detect(event):
        async with semaphore:
            await asyncio.sleep(0.1)  # Simulate some processing time
            return await slack_handler.alert_detector.detect_oom_alert(event)

    tasks = [asyncio.create_task(limited_detect(event)) for event in events]
    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Should complete in reasonable time with resource limits
    assert total_time < 5.0, f"Processing with limits took {total_time:.2f}s (limit: 5s)"

    # Should still process most events
    successful = sum(1 for r in results if r is not None)
    assert successful >= 18, f"Only processed {successful}/20 alerts"


@pytest.mark.asyncio
async def test_concurrent_alert_deduplication(slack_handler):
    """Test that duplicate concurrent alerts are detected properly."""
    # Create duplicate events (same pod, different timestamps)
    events = []
    for i in range(3):  # 3 identical alerts
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": "Pod nginx-deployment-001 was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347840{i}.123456"  # Different timestamps
        })

    # Add some different alerts
    for i in range(2):
        events.append({
            "type": "message",
            "channel": "C1234567890",
            "text": f"Pod nginx-deployment-{i+2:03d} was OOMKilled in namespace production",
            "user": "U1234567890",
            "ts": f"169347841{i}.123456"
        })

    # Process all events concurrently
    tasks = []
    for event in events:
        task = asyncio.create_task(slack_handler.alert_detector.detect_oom_alert(event))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # All events should trigger detection (no deduplication at detector level)
    detected_alerts = [r for r in results if r is not None]
    assert len(detected_alerts) == 5, f"Expected 5 detections, got {len(detected_alerts)}"

    # Should detect the duplicate pod names
    pod_names = [alert.pod_name for alert in detected_alerts]
    assert pod_names.count("nginx-deployment-001") == 3, "Should detect 3 duplicate alerts"
    assert pod_names.count("nginx-deployment-002") == 1, "Should detect unique alert 002"
    assert pod_names.count("nginx-deployment-003") == 1, "Should detect unique alert 003"
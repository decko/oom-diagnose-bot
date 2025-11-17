"""Contract tests for metrics endpoint."""

import re
from unittest.mock import patch

import pytest

from oom_diag_bot.handlers.metrics_handler import MetricsHandler


@pytest.fixture
def metrics_handler():
    """Create a MetricsHandler instance for testing."""
    return MetricsHandler()


@pytest.mark.asyncio
async def test_prometheus_format_compliance(metrics_handler):
    """Test metrics output follows Prometheus format."""
    metrics_output = await metrics_handler.get_metrics()

    # Should be string format
    assert isinstance(metrics_output, str)

    # Parse lines
    lines = metrics_output.strip().split('\n')
    assert len(lines) > 0

    # Check for required metrics
    expected_metrics = [
        "oom_bot_alerts_processed_total",
        "oom_bot_response_duration_seconds",
        "oom_bot_data_source_errors_total",
        "oom_bot_memory_usage_bytes"
    ]

    for metric in expected_metrics:
        assert any(metric in line for line in lines), f"Missing metric: {metric}"


@pytest.mark.asyncio
async def test_help_comments_format(metrics_handler):
    """Test HELP comments follow Prometheus format."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    help_lines = [line for line in lines if line.startswith('# HELP')]

    # Should have HELP comments for each metric
    assert len(help_lines) >= 4

    # HELP format: # HELP metric_name description
    help_pattern = re.compile(r'^# HELP \w+ .+$')
    for help_line in help_lines:
        assert help_pattern.match(help_line), f"Invalid HELP format: {help_line}"


@pytest.mark.asyncio
async def test_type_comments_format(metrics_handler):
    """Test TYPE comments follow Prometheus format."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    type_lines = [line for line in lines if line.startswith('# TYPE')]

    # Should have TYPE comments for each metric
    assert len(type_lines) >= 4

    # TYPE format: # TYPE metric_name metric_type
    valid_types = ['counter', 'gauge', 'histogram', 'summary']
    type_pattern = re.compile(r'^# TYPE (\w+) (\w+)$')

    for type_line in type_lines:
        match = type_pattern.match(type_line)
        assert match, f"Invalid TYPE format: {type_line}"
        metric_type = match.group(2)
        assert metric_type in valid_types, f"Invalid metric type: {metric_type}"


@pytest.mark.asyncio
async def test_counter_metrics_format(metrics_handler):
    """Test counter metrics format."""
    metrics_output = await metrics_handler.get_metrics()

    # Counter metrics should have labels and numeric values
    counter_pattern = re.compile(r'^oom_bot_alerts_processed_total\{status="(success|failed)"\} \d+$')

    lines = metrics_output.strip().split('\n')
    counter_lines = [line for line in lines if line.startswith('oom_bot_alerts_processed_total{')]

    assert len(counter_lines) >= 2  # success and failed counters

    for line in counter_lines:
        assert counter_pattern.match(line), f"Invalid counter format: {line}"


@pytest.mark.asyncio
async def test_histogram_metrics_format(metrics_handler):
    """Test histogram metrics format."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    # Find histogram buckets
    bucket_lines = [line for line in lines if 'oom_bot_response_duration_seconds_bucket' in line]
    assert len(bucket_lines) > 0

    # Bucket format: metric_name_bucket{le="value"} count
    bucket_pattern = re.compile(r'^oom_bot_response_duration_seconds_bucket\{le="([0-9.+]+|\+Inf)"\} \d+$')

    for line in bucket_lines:
        assert bucket_pattern.match(line), f"Invalid bucket format: {line}"

    # Should have +Inf bucket
    inf_buckets = [line for line in bucket_lines if 'le="+Inf"' in line]
    assert len(inf_buckets) == 1


@pytest.mark.asyncio
async def test_gauge_metrics_format(metrics_handler):
    """Test gauge metrics format."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    # Find gauge metrics
    gauge_lines = [line for line in lines if line.startswith('oom_bot_memory_usage_bytes')]

    # Gauge format: metric_name value or metric_name{labels} value
    gauge_pattern = re.compile(r'^oom_bot_memory_usage_bytes(\{[^}]*\})? [0-9.]+$')

    for line in gauge_lines:
        assert gauge_pattern.match(line), f"Invalid gauge format: {line}"


@pytest.mark.asyncio
async def test_metric_labels_validation(metrics_handler):
    """Test metric labels follow naming conventions."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    # Extract lines with labels
    label_lines = [line for line in lines if '{' in line and '}' in line]

    label_pattern = re.compile(r'\{([^}]+)\}')

    for line in label_lines:
        match = label_pattern.search(line)
        if match:
            labels_str = match.group(1)
            label_pairs = labels_str.split(',')

            for pair in label_pairs:
                # Label format: key="value"
                assert '=' in pair, f"Invalid label format in: {line}"
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Key should be valid identifier
                assert re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key), f"Invalid label key: {key}"

                # Value should be quoted
                assert value.startswith('"') and value.endswith('"'), f"Unquoted label value: {value}"


@pytest.mark.asyncio
async def test_metric_values_numeric(metrics_handler):
    """Test all metric values are numeric."""
    metrics_output = await metrics_handler.get_metrics()
    lines = metrics_output.strip().split('\n')

    # Filter out comment lines
    metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]

    for line in metric_lines:
        # Extract value (last space-separated part)
        parts = line.split()
        if len(parts) >= 2:
            value = parts[-1]
            try:
                float(value)
            except ValueError:
                pytest.fail(f"Non-numeric metric value in: {line}")


@pytest.mark.asyncio
async def test_content_type_header(metrics_handler):
    """Test metrics endpoint returns correct content type."""
    content_type = await metrics_handler.get_content_type()

    # Prometheus expects text/plain
    assert content_type == "text/plain"


@pytest.mark.asyncio
async def test_metrics_collection_state(metrics_handler):
    """Test metrics reflect current application state."""
    # Simulate some application activity
    with patch.object(metrics_handler, 'alerts_processed_success', 42):
        with patch.object(metrics_handler, 'alerts_processed_failed', 3):
            metrics_output = await metrics_handler.get_metrics()

            # Should contain the current values
            assert 'oom_bot_alerts_processed_total{status="success"} 42' in metrics_output
            assert 'oom_bot_alerts_processed_total{status="failed"} 3' in metrics_output


@pytest.mark.asyncio
async def test_response_size_reasonable(metrics_handler):
    """Test metrics response size is reasonable."""
    metrics_output = await metrics_handler.get_metrics()

    # Should be reasonable size (less than 10KB for basic metrics)
    assert len(metrics_output.encode('utf-8')) < 10240


@pytest.mark.asyncio
async def test_metrics_monotonic_counters(metrics_handler):
    """Test counter metrics are monotonic (never decrease)."""
    # Get initial metrics
    metrics1 = await metrics_handler.get_metrics()

    # Simulate activity
    with patch.object(metrics_handler, 'increment_alerts_processed'):
        await metrics_handler.increment_alerts_processed('success')

    # Get updated metrics
    metrics2 = await metrics_handler.get_metrics()

    # Parse counter values
    def extract_counter_value(metrics_text: str, status: str) -> int:
        pattern = f'oom_bot_alerts_processed_total{{status="{status}"}} (\\d+)'
        match = re.search(pattern, metrics_text)
        return int(match.group(1)) if match else 0

    success_count1 = extract_counter_value(metrics1, 'success')
    success_count2 = extract_counter_value(metrics2, 'success')

    # Counter should not decrease
    assert success_count2 >= success_count1
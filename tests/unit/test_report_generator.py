"""Unit tests for ReportGenerator service."""

from datetime import datetime

import pytest

from oom_diag_bot.models.oom_alert import OOMAlert
from oom_diag_bot.services.report_generator import ReportGenerator


@pytest.fixture
def sample_alert():
    """Fixture providing a valid OOM alert for testing."""
    return OOMAlert(
        pod_name="nginx-deployment-abc123",
        namespace="production",
        message_id="1693478400.123456",
        channel_id="C1234567890",
        raw_content="Pod nginx-deployment-abc123 was OOMKilled in namespace production",
        keywords_matched=["OOMKilled"],
        user_id="U1234567890",
        container_name="pulp-content",
        timestamp=datetime.fromtimestamp(1693478400.123456)
    )


@pytest.fixture
def report_generator():
    """Fixture providing a ReportGenerator instance."""
    return ReportGenerator()


def test_parse_memory_value_mi(report_generator):
    """Test memory parsing with Mi suffix."""
    result = report_generator._parse_memory_value("256Mi")
    assert result == 268435456  # 256 * 1024 * 1024


def test_parse_memory_value_gi(report_generator):
    """Test memory parsing with Gi suffix."""
    result = report_generator._parse_memory_value("2Gi")
    assert result == 2147483648  # 2 * 1024 * 1024 * 1024


def test_parse_memory_value_invalid(report_generator):
    """Test memory parsing with invalid format."""
    result = report_generator._parse_memory_value("invalid")
    assert result is None


def test_parse_cpu_value_millicores(report_generator):
    """Test CPU parsing with millicores."""
    result = report_generator._parse_cpu_value("500m")
    assert result == 500


def test_parse_cpu_value_cores(report_generator):
    """Test CPU parsing with cores."""
    result = report_generator._parse_cpu_value("2")
    assert result == 2000  # 2 cores = 2000 millicores


def test_parse_cpu_value_invalid(report_generator):
    """Test CPU parsing with invalid format."""
    with pytest.raises(ValueError):
        report_generator._parse_cpu_value("invalid")


def test_get_total_restart_count_with_containers(report_generator):
    """Test restart count calculation with container statuses."""
    status = {
        "containerStatuses": [
            {"restartCount": 5},
            {"restartCount": 3}
        ]
    }
    result = report_generator._get_total_restart_count(status)
    assert result == 8


def test_get_total_restart_count_no_containers(report_generator):
    """Test restart count calculation with no containers."""
    status = {}
    result = report_generator._get_total_restart_count(status)
    assert result == 0


def test_determine_log_level_error(report_generator):
    """Test log level determination for error messages."""
    message = "ERROR: OutOfMemoryError occurred"
    result = report_generator._determine_log_level(message)
    assert result == "ERROR"


def test_determine_log_level_warning(report_generator):
    """Test log level determination for warning messages."""
    message = "WARN: Memory usage is high"
    result = report_generator._determine_log_level(message)
    assert result == "WARN"


def test_determine_log_level_info(report_generator):
    """Test log level determination for info messages."""
    message = "Pod started successfully"
    result = report_generator._determine_log_level(message)
    assert result == "INFO"

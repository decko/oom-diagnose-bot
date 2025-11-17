"""Unit tests for model validation."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from oom_diag_bot.models.bot_configuration import BotConfiguration
from oom_diag_bot.models.cloudwatch_logs import CloudWatchLogs
from oom_diag_bot.models.container_information import ContainerInformation
from oom_diag_bot.models.data_source_config import DataSourceConfig
from oom_diag_bot.models.diagnostic_report import DiagnosticReport
from oom_diag_bot.models.oom_alert import OOMAlert
from oom_diag_bot.models.pod_information import PodInformation
from oom_diag_bot.models.prometheus_metrics import PrometheusMetrics


def test_valid_oom_alert():
    """Test creating valid OOM alert."""
    alert = OOMAlert(
        pod_name="nginx-deployment-abc123",
        namespace="production",
        message_id="1693478400.123456",
        channel_id="C1234567890",
        raw_content="Pod nginx-deployment-abc123 was OOMKilled",
        keywords_matched=["OOMKilled"],
        user_id="U1234567890",
        timestamp=datetime.now()
    )

    assert alert.pod_name == "nginx-deployment-abc123"
    assert alert.namespace == "production"
    assert alert.channel_id == "C1234567890"


class TestOOMAlertValidation:
    """Test OOMAlert model validation."""

def test_invalid_pod_name():
    """Test validation with invalid pod name."""
    with pytest.raises(ValidationError, match="Invalid pod name format"):
        OOMAlert(
            pod_name="INVALID_POD_NAME",  # Uppercase not allowed
            namespace="production",
            message_id="1693478400.123456",
            channel_id="C1234567890",
            raw_content="Test message",
            keywords_matched=["OOMKilled"],
            user_id="U1234567890",
            timestamp=datetime.now()
        )

def test_invalid_namespace():
    """Test validation with invalid namespace."""
    with pytest.raises(ValidationError, match="Invalid namespace format"):
        OOMAlert(
            pod_name="valid-pod",
            namespace="INVALID_NAMESPACE",  # Uppercase not allowed
            message_id="1693478400.123456",
            channel_id="C1234567890",
            raw_content="Test message",
            keywords_matched=["OOMKilled"],
            user_id="U1234567890",
            timestamp=datetime.now()
        )

def test_invalid_channel_id():
    """Test validation with invalid Slack channel ID."""
    with pytest.raises(ValidationError, match="Invalid channel ID format"):
        OOMAlert(
            pod_name="valid-pod",
            namespace="production",
            message_id="1693478400.123456",
            channel_id="invalid-channel",  # Must start with C
            raw_content="Test message",
            keywords_matched=["OOMKilled"],
            user_id="U1234567890",
            timestamp=datetime.now()
        )

def test_invalid_message_id():
    """Test validation with invalid Slack message ID."""
    with pytest.raises(ValidationError, match="Invalid message ID format"):
        OOMAlert(
            pod_name="valid-pod",
            namespace="production",
            message_id="invalid.message.id",  # Wrong format
            channel_id="C1234567890",
            raw_content="Test message",
            keywords_matched=["OOMKilled"],
            user_id="U1234567890",
            timestamp=datetime.now()
        )


@pytest.fixture
def valid_oom_alert():
    """Fixture providing a valid OOM alert for testing."""
    return OOMAlert(
        pod_name="nginx-deployment-abc123",
        namespace="production",
        message_id="1693478400.123456",
        channel_id="C1234567890",
        raw_content="Pod nginx-deployment-abc123 was OOMKilled",
        keywords_matched=["OOMKilled"],
        user_id="U1234567890",
        timestamp=datetime.now()
    )


def test_valid_diagnostic_report(valid_oom_alert):
    """Test creating valid diagnostic report."""
    report = DiagnosticReport(
        alert_id="test-alert-123",
        generation_timestamp=datetime.now(),
        summary="Test OOM incident summary",
        data_sources_available=["openshift", "prometheus"],
        recommendations=["Increase memory limit"]
    )

    assert report.alert_id == "test-alert-123"
    assert len(report.recommendations) == 1
    assert "openshift" in report.data_sources_available


def test_empty_data_sources_validation():
    """Test that at least one data source must be available."""
    with pytest.raises(
        ValidationError, match="At least one data source must be available"
    ):
        DiagnosticReport(
            alert_id="test-alert-123",
            generation_timestamp=datetime.now(),
            summary="Test OOM incident summary",
            data_sources_available=[],  # Empty list not allowed
            recommendations=["Increase memory limit"]
        )


# Diagnostic Report validation tests completed above

def test_valid_pod_information():
    """Test creating valid pod information."""
    pod_info = PodInformation(
        name="nginx-deployment-abc123",
        namespace="production",
        status="Running",
        creation_timestamp=datetime.now(),
        restart_count=5,
        containers=[
            ContainerInformation(
                name="nginx",
                image="nginx:latest",
                ready=True,
                started=True
            )
        ]
    )

    assert pod_info.name == "nginx-deployment-abc123"
    assert len(pod_info.containers) == 1

def test_negative_restart_count():
    """Test validation with negative restart count."""
    with pytest.raises(
        ValidationError, match="Input should be greater than or equal to 0"
    ):
        PodInformation(
            name="nginx-deployment-abc123",
            namespace="production",
            status="Running",
            creation_timestamp=datetime.now(),
            restart_count=-1,  # Negative not allowed
            containers=[]
        )


def test_valid_container_information():
    """Test creating valid container information."""
    container = ContainerInformation(
        name="nginx",
        image="nginx:1.21",
        ready=True,
        started=True
    )

    assert container.name == "nginx"
    assert container.image == "nginx:1.21"


def test_invalid_container_name():
    """Test validation with invalid container name."""
    with pytest.raises(ValidationError, match="Invalid container name format"):
        ContainerInformation(
            name="INVALID_CONTAINER",  # Uppercase not allowed
            image="nginx:latest",
            ready=True,
            started=True
        )


def test_valid_prometheus_metrics():
    """Test creating valid Prometheus metrics."""
    metrics = PrometheusMetrics(
        pod_name="nginx-deployment-abc123",
        namespace="production",
        memory_usage_current=268435456,  # 256MB
        memory_limit=536870912,  # 512MB
        cpu_usage_current=50.0,
        oom_kills_total=3,
        query_timestamp=datetime.now()
    )

    assert metrics.memory_usage_current == 268435456
    assert metrics.cpu_usage_current == 50.0

def test_negative_memory_values():
    """Test validation with negative memory values."""
    with pytest.raises(
        ValidationError, match="Input should be greater than or equal to 0"
    ):
        PrometheusMetrics(
            pod_name="nginx-deployment-abc123",
            namespace="production",
            memory_usage_current=-1,  # Negative not allowed
            memory_limit=536870912,
            cpu_usage_current=50.0,
            oom_kills_total=3,
            query_timestamp=datetime.now()
        )

def test_negative_cpu_values():
    """Test validation with negative CPU values."""
    with pytest.raises(
        ValidationError, match="Input should be greater than or equal to 0"
    ):
        PrometheusMetrics(
            pod_name="nginx-deployment-abc123",
            namespace="production",
            memory_usage_current=268435456,
            memory_limit=536870912,
            cpu_usage_current=-0.1,  # Negative not allowed
            oom_kills_total=3,
            query_timestamp=datetime.now()
        )


def test_valid_cloudwatch_logs():
    """Test creating valid CloudWatch logs."""
    logs = CloudWatchLogs(
        log_group="/aws/eks/cluster",
        log_stream="pod-stream",
        timestamp=datetime.now(),
        message="ERROR: OutOfMemoryError",
        level="ERROR"
    )

    assert logs.log_group == "/aws/eks/cluster"
    assert logs.message == "ERROR: OutOfMemoryError"


def test_cloudwatch_logs_message_too_long():
    """Test validation with message that's too long."""
    with pytest.raises(
        ValidationError, match="String should have at most 10000 characters"
    ):
        CloudWatchLogs(
            log_group="/aws/eks/cluster",
            log_stream="pod-stream",
            timestamp=datetime.now(),
            message="x" * 15000,  # Too long (over 10000 characters)
            level="ERROR"
        )


def test_valid_data_source_config():
    """Test creating valid data source config."""
    config = DataSourceConfig(
        name="openshift",
        enabled=True,
        endpoint_url="https://api.openshift.example.com",
        timeout_seconds=30,
        retry_attempts=3,
        authentication_type="token",
        connection_pool_size=10
    )

    assert config.name == "openshift"
    assert config.endpoint_url == "https://api.openshift.example.com"

def test_invalid_endpoint_url():
    """Test validation with invalid endpoint URL."""
    with pytest.raises(ValidationError, match="Endpoint URL must start with http:// or https://"):
        DataSourceConfig(
            name="openshift",
            enabled=True,
            endpoint_url="not-a-url",  # Invalid URL
            timeout_seconds=30,
            retry_attempts=3,
            authentication_type="token",
            connection_pool_size=10
        )

def test_invalid_data_source_name():
    """Test validation with invalid data source name."""
    with pytest.raises(ValidationError, match="Invalid data source name"):
        DataSourceConfig(
            name="invalid-source",  # Not in allowed list
            enabled=True,
            endpoint_url="https://api.example.com",
            timeout_seconds=30,
            retry_attempts=3,
            authentication_type="token",
            connection_pool_size=10
        )


def test_valid_bot_configuration():
    """Test creating valid bot configuration."""
    config = BotConfiguration(
        monitored_channels=["C1234567890", "C0987654321"],
        oom_keywords=["OOMKilled", "memory limit exceeded"],
        response_template="Default template",
        rate_limit_per_minute=60,
        debug_mode=False,
        health_check_interval=30
    )

    assert len(config.monitored_channels) == 2
    assert config.rate_limit_per_minute == 60

def test_invalid_channel_id_format():
    """Test validation with invalid channel ID format."""
    with pytest.raises(ValidationError, match="Invalid channel ID format"):
        BotConfiguration(
            monitored_channels=["invalid-channel"],  # Wrong format
            oom_keywords=["OOMKilled"],
            response_template="Default template",
            rate_limit_per_minute=60,
            debug_mode=False,
            health_check_interval=30
        )


def test_empty_oom_keywords():
    """Test validation with empty OOM keywords."""
    with pytest.raises(
        ValidationError, match="At least one OOM keyword must be configured"
    ):
        BotConfiguration(
            monitored_channels=["C1234567890"],
            oom_keywords=[],  # Empty list not allowed
            response_template="Default template",
            rate_limit_per_minute=60,
            debug_mode=False,
            health_check_interval=30
        )


def test_invalid_rate_limit():
    """Test validation with invalid rate limit."""
    with pytest.raises(
        ValidationError, match="Input should be greater than or equal to 1"
    ):
        BotConfiguration(
            monitored_channels=["C1234567890"],
            oom_keywords=["OOMKilled"],
            response_template="Default template",
            rate_limit_per_minute=0,  # Too low
            debug_mode=False,
            health_check_interval=30
        )

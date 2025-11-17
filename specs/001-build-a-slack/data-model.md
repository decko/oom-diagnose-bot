# Data Model: Slack OOM Diagnostic Bot

## Core Entities

### OOMAlert
Represents a detected out-of-memory incident extracted from Slack messages.

**Attributes**:
- `message_id`: Slack message identifier for threading responses
- `channel_id`: Slack channel where alert was detected
- `timestamp`: Alert detection timestamp (ISO 8601)
- `raw_content`: Original alert message content
- `pod_name`: Extracted Kubernetes pod name
- `namespace`: Extracted Kubernetes namespace
- `container_name`: Extracted container name (optional)
- `keywords_matched`: List of OOM keywords that triggered detection
- `user_id`: Slack user who posted the original alert

**Validation Rules**:
- `message_id` must be valid Slack message ID format
- `pod_name` and `namespace` must match Kubernetes naming conventions
- `timestamp` must be valid ISO 8601 format
- `keywords_matched` must contain at least one configured OOM keyword

**State Transitions**:
- DETECTED → PROCESSING → COMPLETED/FAILED

### DiagnosticReport
Contains structured diagnostic information collected from multiple sources.

**Attributes**:
- `alert_id`: Reference to originating OOMAlert
- `generation_timestamp`: Report creation timestamp
- `openshift_data`: Pod information from OpenShift API
- `prometheus_metrics`: Memory usage metrics and trends
- `cloudwatch_logs`: Relevant log entries from incident timeframe
- `summary`: Human-readable incident summary
- `recommendations`: Suggested remediation actions
- `data_sources_available`: List of successfully queried sources
- `errors`: Collection errors from unavailable sources

**Validation Rules**:
- Must contain data from at least one source
- `generation_timestamp` must be after associated alert timestamp
- All metric values must be non-negative numbers
- Log entries must include timestamps and sources

### PodInformation
Kubernetes pod metadata retrieved from OpenShift.

**Attributes**:
- `name`: Pod name
- `namespace`: Pod namespace
- `status`: Current pod status (Running, Pending, Failed, etc.)
- `memory_request`: Configured memory request in bytes
- `memory_limit`: Configured memory limit in bytes
- `cpu_request`: Configured CPU request in millicores
- `cpu_limit`: Configured CPU limit in millicores
- `creation_timestamp`: Pod creation time
- `restart_count`: Number of container restarts
- `node_name`: Node where pod is scheduled
- `labels`: Pod labels as key-value pairs
- `annotations`: Pod annotations as key-value pairs

**Relationships**:
- One-to-many with ContainerInformation
- Many-to-one with NodeInformation

### ContainerInformation
Individual container details within a pod.

**Attributes**:
- `name`: Container name
- `image`: Container image name and tag
- `memory_usage`: Current memory usage in bytes
- `cpu_usage`: Current CPU usage in millicores
- `restart_count`: Container-specific restart count
- `last_termination_reason`: Reason for last termination (if any)
- `ready`: Container readiness status
- `started`: Container started status

### PrometheusMetrics
Memory and resource usage metrics from Prometheus.

**Attributes**:
- `pod_name`: Target pod name
- `namespace`: Target namespace
- `memory_usage_current`: Current memory usage in bytes
- `memory_usage_average_1h`: Average memory usage over 1 hour
- `memory_usage_peak_24h`: Peak memory usage in last 24 hours
- `memory_limit`: Configured memory limit
- `oom_kills_total`: Total OOM kills for this pod
- `cpu_usage_current`: Current CPU usage percentage
- `network_io_bytes`: Network I/O in bytes
- `filesystem_usage_bytes`: Filesystem usage in bytes
- `query_timestamp`: Metrics collection timestamp

### CloudWatchLogs
Log entries related to the OOM incident.

**Attributes**:
- `log_group`: CloudWatch log group name
- `log_stream`: CloudWatch log stream name
- `timestamp`: Log entry timestamp
- `message`: Log message content
- `level`: Log level (ERROR, WARN, INFO, DEBUG)
- `source`: Log source identifier
- `request_id`: Request correlation ID (if available)

### DataSourceConfig
Configuration for external data source connections.

**Attributes**:
- `name`: Data source identifier (openshift, prometheus, cloudwatch)
- `enabled`: Whether this data source is active
- `endpoint_url`: API endpoint URL
- `timeout_seconds`: Request timeout configuration
- `retry_attempts`: Number of retry attempts for failed requests
- `authentication_type`: Authentication method (token, iam, oauth)
- `connection_pool_size`: Maximum concurrent connections

### BotConfiguration
Bot operational configuration and settings.

**Attributes**:
- `monitored_channels`: List of Slack channel IDs to monitor
- `oom_keywords`: List of keywords that trigger OOM detection
- `response_template`: Template for diagnostic report formatting
- `rate_limit_per_minute`: Maximum responses per minute
- `debug_mode`: Enable detailed logging and debugging
- `health_check_interval`: Health check frequency in seconds

## Data Relationships

```
OOMAlert (1) → (1) DiagnosticReport
OOMAlert (1) → (1) PodInformation
PodInformation (1) → (*) ContainerInformation
DiagnosticReport (1) → (*) PrometheusMetrics
DiagnosticReport (1) → (*) CloudWatchLogs
BotConfiguration (1) → (*) DataSourceConfig
```

## Processing Flow

1. **Alert Detection**: Parse Slack message → Create OOMAlert
2. **Data Collection**: Query external sources → Populate metrics/logs
3. **Report Generation**: Aggregate data → Create DiagnosticReport
4. **Response Formatting**: Apply template → Post to Slack thread

## Error Handling

- Partial data collection continues if individual sources fail
- Missing data sources are clearly indicated in reports
- All errors are logged with correlation IDs for debugging
- Timeout handling prevents blocking on slow external services
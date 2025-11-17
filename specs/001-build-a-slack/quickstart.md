# Quickstart: Slack OOM Diagnostic Bot

## Prerequisites

- Python 3.11+ installed
- Access to Slack workspace with bot creation permissions
- OpenShift cluster with read access
- Prometheus instance with cluster metrics
- AWS account with CloudWatch Logs access

## Quick Setup

### 1. Environment Configuration

```bash
# Create environment file
cat > .env << EOF
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# OpenShift Configuration
OPENSHIFT_TOKEN=your-service-account-token
OPENSHIFT_API_URL=https://api.your-cluster.com:6443

# Prometheus Configuration
PROMETHEUS_URL=https://prometheus.your-cluster.com
PROMETHEUS_TOKEN=your-prometheus-token

# AWS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1

# Bot Configuration
MONITORED_CHANNELS=C1234567890,C0987654321
OOM_KEYWORDS=OOMKilled,memory limit exceeded,killed due to memory
DEBUG_MODE=false
EOF
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Bot

```bash
python -m oom_diag_bot.main
```

## Quick Test

### 1. Verify Bot Health

```bash
curl http://localhost:3000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-26T10:00:00Z",
  "data_sources": {
    "openshift": "available",
    "prometheus": "available",
    "cloudwatch": "available"
  },
  "uptime_seconds": 60
}
```

### 2. Test OOM Detection

Post this message in a monitored Slack channel:
```
🚨 ALERT: Pod my-app-abc123 in namespace production was OOMKilled
Container: my-app
Memory limit: 512Mi
```

Expected behavior:
- Bot detects OOM keywords
- Extracts pod name: `my-app-abc123`
- Extracts namespace: `production`
- Responds in thread with diagnostic report within 30 seconds

### 3. Verify Diagnostic Report

The bot should respond with a formatted message containing:

```
🔍 **OOM Diagnostic Report**
**Pod**: my-app-abc123
**Namespace**: production
**Detected**: 2025-09-26 10:05:00 UTC

📊 **Current Status** (OpenShift)
- Status: Failed
- Memory Limit: 512Mi
- Memory Request: 256Mi
- Restart Count: 3

📈 **Memory Usage** (Prometheus)
- Current Usage: 534Mi (104% of limit)
- Average (1h): 445Mi
- Peak (24h): 612Mi
- OOM Kills Total: 3

📋 **Recent Logs** (CloudWatch)
```
2025-09-26 10:04:45 ERROR OutOfMemoryError: Java heap space
2025-09-26 10:04:50 WARN Memory usage critical: 98%
2025-09-26 10:04:55 INFO Pod terminated with exit code 137
```

💡 **Recommendations**
- Increase memory limit to 1Gi based on peak usage
- Review application memory allocation patterns
- Consider implementing memory leak detection
```

## Validation Steps

### 1. Test Error Handling

Test bot behavior when external services are unavailable:

```bash
# Simulate OpenShift API unavailability
# Expect partial report with clear error indication
```

### 2. Test Rate Limiting

Send multiple OOM alerts rapidly:
- Bot should handle concurrent alerts
- Each alert gets individual response
- No response duplication or mixing

### 3. Test Configuration Changes

```bash
# Update monitored channels
export MONITORED_CHANNELS=C1111111111,C2222222222

# Update keywords
export OOM_KEYWORDS="OutOfMemory,memory exceeded,killed,OOM"

# Restart bot and verify new configuration
```

### 4. Test Performance

Generate load test with 10 concurrent OOM alerts:
- All reports generated within 30 seconds
- Memory usage stays under 100MB
- No failed responses due to timeouts

## Troubleshooting

### Bot Not Responding

1. Check health endpoint: `curl http://localhost:3000/health`
2. Verify Slack token permissions in app settings
3. Confirm bot is invited to monitored channels
4. Check logs for authentication errors

### Partial Diagnostic Data

1. Test individual data source connectivity
2. Verify service account permissions for OpenShift
3. Check Prometheus query syntax and data availability
4. Validate AWS CloudWatch access and log groups

### Slow Response Times

1. Check external API response times
2. Monitor network connectivity to data sources
3. Review timeout configurations
4. Check for API rate limiting

## Success Criteria

- [x] Bot responds to OOM alerts within 30 seconds
- [x] Diagnostic reports include data from all available sources
- [x] Bot handles multiple concurrent alerts correctly
- [x] Partial reports generated when some data sources unavailable
- [x] Memory usage stays under 100MB during operation
- [x] Health endpoint reports accurate service status
- [x] Logs provide sufficient detail for troubleshooting
- [x] Bot configuration can be updated without code changes

## Metrics Monitoring

Access operational metrics:
```bash
curl http://localhost:3000/metrics
```

Key metrics to monitor:
- `oom_bot_alerts_processed_total` - Total alerts processed
- `oom_bot_response_duration_seconds` - Response time distribution
- `oom_bot_data_source_errors_total` - External API failures
- `oom_bot_memory_usage_bytes` - Bot memory consumption
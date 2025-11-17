# OOM Diagnostic Bot

A Slack bot that monitors alert channels for Out-of-Memory (OOM) incidents and automatically responds with comprehensive diagnostic information from OpenShift, Prometheus, and AWS CloudWatch.

## Features

- **Automatic OOM Detection**: Monitors Slack channels for OOM-related keywords
- **Multi-Source Data Collection**: Gathers diagnostic data from:
  - OpenShift/Kubernetes API (pod information, resource limits, status)
  - Prometheus (memory metrics, usage trends, restart counts)
  - AWS CloudWatch (application logs, error messages)
- **Intelligent Report Generation**: Creates structured diagnostic reports with actionable recommendations
- **Slack Integration**: Posts diagnostic reports as threaded replies to OOM alerts
- **High Performance**: Concurrent data collection with <30s response time and <100MB memory usage

## Architecture

The bot follows a service-oriented architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Slack Events   │───▶│   Alert Detector │───▶│ Report Generator│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        ▲
                                ▼                        │
                       ┌──────────────────┐              │
                       │  Data Collector  │──────────────┘
                       └──────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌─────────────┐ ┌─────────┐ ┌─────────────┐
            │ OpenShift   │ │Prometheus│ │ CloudWatch  │
            │   Client    │ │ Client  │ │   Client    │
            └─────────────┘ └─────────┘ └─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Slack workspace with bot permissions
- Access to OpenShift/Kubernetes cluster (optional)
- Prometheus instance (optional)
- AWS account with CloudWatch access (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd oom-diag-bot
```

2. Install dependencies:

**Using uv (recommended - faster and better dependency resolution):**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the bot
uv run python -m oom_diag_bot.main
```

**Using pip:**
```bash
pip install -r requirements.txt
python -m oom_diag_bot.main
```

3. Configure environment variables (see [Configuration](#configuration)):
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Docker Deployment

```bash
docker build -t oom-diag-bot .
docker run --env-file .env oom-diag-bot
```

Or using docker-compose:
```bash
docker-compose up -d
```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token | `xoxb-123...` |
| `SLACK_APP_TOKEN` | App-Level Token | `xapp-1-A123...` |
| `SLACK_SIGNING_SECRET` | Signing Secret | `abc123...` |
| `MONITORED_CHANNELS` | Comma-separated channel IDs | `C1234567890,C0987654321` |

### Optional Data Sources

#### OpenShift/Kubernetes
| Variable | Description | Default |
|----------|-------------|---------|
| `OPENSHIFT_API_URL` | API server URL | None |
| `OPENSHIFT_TOKEN` | Service account token | None |

#### Prometheus
| Variable | Description | Default |
|----------|-------------|---------|
| `PROMETHEUS_URL` | Prometheus server URL | None |
| `PROMETHEUS_TOKEN` | Bearer token | None |

#### AWS CloudWatch
| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | None |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | None |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |

### Bot Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `OOM_KEYWORDS` | Comma-separated OOM keywords | `OOMKilled,memory limit exceeded,killed due to memory` |
| `DEBUG_MODE` | Enable debug logging | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REQUEST_TIMEOUT` | API request timeout (seconds) | `30` |

## Usage

### Slack Bot Setup

1. Create a new Slack app at https://api.slack.com/apps
2. Configure OAuth & Permissions:
   - Add bot scope: `chat:write`
   - Add bot scope: `channels:history`
   - Add bot scope: `groups:history`
3. Enable Socket Mode and create an App-Level Token
4. Install the app to your workspace
5. Invite the bot to channels you want to monitor

### Monitoring Channels

The bot monitors specified Slack channels for messages containing OOM keywords:
- `OOMKilled`
- `memory limit exceeded`
- `killed due to memory`

When detected, it extracts pod and namespace information and generates a diagnostic report.

### Example Alert Detection

**Input message:**
```
Pod nginx-deployment-abc123 was OOMKilled in namespace production
```

**Bot response:**
```
🔍 OOM Diagnostic Report for nginx-deployment-abc123

📊 Memory Analysis:
• Current Usage: 245 MB (96% of limit)
• Memory Limit: 256 MB
• Status: OVER_LIMIT

🔧 OpenShift Information:
• Namespace: production
• Restart Count: 5
• Last Termination: OOMKilled (exit code 137)

📈 Prometheus Metrics:
• 24h Restart Count: 12
• Memory Working Set: 234 MB

📋 CloudWatch Logs:
• Found 3 relevant log entries
• Latest: ERROR: OutOfMemoryError in nginx process

💡 Recommendations:
• Increase memory limit from 256MB to 512MB
• Review application memory usage patterns
• Consider implementing memory monitoring alerts
```

## Development

### Project Structure

```
src/oom_diag_bot/
├── main.py                 # Application entry point
├── config/
│   └── config_loader.py    # Configuration management
├── models/
│   ├── oom_alert.py       # OOM alert data model
│   ├── diagnostic_report.py # Report data model
│   └── ...                # Other data models
├── services/
│   ├── alert_detector.py  # OOM detection logic
│   ├── report_generator.py # Report generation
│   ├── data_collector.py  # Multi-source data collection
│   └── ...                # External API clients
├── handlers/
│   ├── slack_handler.py   # Slack event handling
│   ├── health_handler.py  # Health check endpoint
│   └── metrics_handler.py # Metrics endpoint
└── utils/
    ├── logging_setup.py   # Structured logging
    └── error_handler.py   # Error handling utilities
```

### Running Tests

**Using uv:**
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/performance/
uv run pytest tests/contract/

# Run with coverage
uv run pytest --cov=oom_diag_bot --cov-report=html
```

**Using pip:**
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
pytest tests/contract/

# Run with coverage
pytest --cov=oom_diag_bot --cov-report=html
```

### Code Quality

**Using uv:**
```bash
# Check and fix code quality issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

**Using traditional tools:**
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Health & Metrics

The bot exposes health and metrics endpoints:

- **Health**: `GET /health` - Application health status
- **Metrics**: `GET /metrics` - Prometheus-compatible metrics

## Performance

The bot is designed to meet strict performance requirements:

- **Response Time**: <30 seconds end-to-end processing
- **Memory Usage**: <100MB total memory consumption
- **Concurrency**: Handles multiple simultaneous alerts efficiently
- **Reliability**: Graceful degradation when data sources are unavailable

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes following the coding standards
4. Add tests for new functionality
5. Run the full test suite: `pytest`
6. Commit changes: `git commit -m "Add new feature"`
7. Push to the branch: `git push origin feature/new-feature`
8. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation for troubleshooting guides
- Review logs for error details (use `DEBUG_MODE=true` for verbose logging)
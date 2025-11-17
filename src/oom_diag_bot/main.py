"""Main application entry point."""

import asyncio
import signal
import sys

import structlog
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .config.config_loader import load_config, setup_logging, validate_required_config
from .handlers.health_handler import HealthHandler
from .handlers.metrics_handler import MetricsHandler
from .handlers.slack_handler import SlackEventHandler
from .services.alert_detector import AlertDetector
from .services.cloudwatch_client import CloudWatchClient
from .services.data_collector import DataCollector
from .services.openshift_client import OpenShiftClient
from .services.prometheus_client import PrometheusClient
from .services.report_generator import ReportGenerator

logger = structlog.get_logger(__name__)


class OOMDiagnosticBot:
    """Main application class for OOM Diagnostic Bot."""

    def __init__(self):
        """Initialize the bot."""
        self.config = None
        self.slack_app = None
        self.slack_handler = None
        self.health_handler = None
        self.metrics_handler = None
        self.socket_mode_handler = None
        self.running = False

    async def initialize(self) -> None:
        """Initialize bot components."""
        try:
            # Load configuration
            self.config = load_config()
            validate_required_config(self.config)
            setup_logging(self.config)

            logger.info("Starting OOM Diagnostic Bot initialization")

            # Initialize Slack app (async version)
            self.slack_app = AsyncApp(
                token=self.config.slack_bot_token,
                signing_secret=self.config.slack_signing_secret,
            )

            # Initialize external clients
            openshift_client = None
            if self.config.openshift_token and self.config.openshift_api_url:
                openshift_client = OpenShiftClient(
                    api_url=self.config.openshift_api_url,
                    token=self.config.openshift_token,
                    timeout=self.config.request_timeout,
                )

            prometheus_client = None
            if self.config.prometheus_url:
                prometheus_client = PrometheusClient(
                    url=self.config.prometheus_url,
                    token=self.config.prometheus_token,
                    timeout=self.config.request_timeout,
                )

            cloudwatch_client = None
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                cloudwatch_client = CloudWatchClient(
                    region=self.config.aws_default_region,
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key,
                    timeout=self.config.request_timeout,
                )

            # Initialize services
            alert_detector = AlertDetector(oom_keywords=self.config.oom_keywords)
            DataCollector(
                openshift_client=openshift_client,
                prometheus_client=prometheus_client,
                cloudwatch_client=cloudwatch_client,
            )
            report_generator = ReportGenerator()

            # Initialize handlers
            self.slack_handler = SlackEventHandler(
                slack_app=self.slack_app,
                alert_detector=alert_detector,
                report_generator=report_generator,
            )
            self.health_handler = HealthHandler()
            self.metrics_handler = MetricsHandler()

            # Setup Slack event handlers
            self._setup_slack_handlers()

            # Initialize Socket Mode handler (async version)
            self.socket_mode_handler = AsyncSocketModeHandler(
                app=self.slack_app, app_token=self.config.slack_app_token
            )

            logger.info("Bot initialization completed successfully")

        except Exception as e:
            logger.error("Bot initialization failed", error=str(e))
            raise

    def _setup_slack_handlers(self) -> None:
        """Setup Slack event handlers."""

        @self.slack_app.event("message")
        async def handle_message_events(body, logger):
            """Handle message events."""
            try:
                event = body.get("event", {})

                # Log all incoming messages for debugging
                structlog.get_logger(__name__).debug(
                    "Received message event",
                    channel=event.get("channel"),
                    user=event.get("user"),
                    text=event.get("text", "")[:100],
                    subtype=event.get("subtype")
                )

                # Skip if not in monitored channels
                if not self.slack_handler.alert_detector.should_process_message(
                    event, self.config.monitored_channels_list
                ):
                    structlog.get_logger(__name__).debug(
                        "Message skipped - not in monitored channels or invalid",
                        channel=event.get("channel"),
                        monitored=self.config.monitored_channels_list
                    )
                    return

                await self.slack_handler._handle_message_event(event)

            except Exception as e:
                logger.error("Error handling message event", error=str(e))

        @self.slack_app.event("app_mention")
        async def handle_mentions(body, logger):
            """Handle app mentions."""
            try:
                event = body.get("event", {})
                await self.slack_handler.handle_mention(event)
            except Exception as e:
                logger.error("Error handling mention", error=str(e))

    async def start(self) -> None:
        """Start the bot."""
        try:
            if not self.socket_mode_handler:
                await self.initialize()

            logger.info("Starting OOM Diagnostic Bot")
            self.running = True

            # Start async Socket Mode handler
            await self.socket_mode_handler.start_async()

            logger.info("Bot started successfully")

        except Exception as e:
            logger.error("Failed to start bot", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        try:
            logger.info("Stopping OOM Diagnostic Bot")
            self.running = False

            if self.socket_mode_handler:
                await self.socket_mode_handler.close_async()

            logger.info("Bot stopped successfully")

        except Exception as e:
            logger.error("Error stopping bot", error=str(e))

    async def run_forever(self) -> None:
        """Run the bot until interrupted."""
        try:
            await self.start()

            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error("Bot crashed", error=str(e))
            raise
        finally:
            await self.stop()


async def main() -> None:
    """Main entry point."""
    bot = OOMDiagnosticBot()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        bot.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.run_forever()
    except Exception as e:
        logger.error("Application error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

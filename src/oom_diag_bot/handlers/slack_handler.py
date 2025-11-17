"""Slack Event Handler for processing Slack events and interactions."""

import json
from typing import Any

import structlog
from slack_bolt import App

from ..models.oom_alert import OOMAlert
from ..services.alert_detector import AlertDetector
from ..services.report_generator import ReportGenerator

logger = structlog.get_logger(__name__)


class SlackEventHandler:
    """Handler for Slack events and interactions."""

    def __init__(
        self,
        slack_app: App,
        alert_detector: AlertDetector,
        report_generator: ReportGenerator,
    ):
        """Initialize SlackEventHandler."""
        self.app = slack_app
        self.alert_detector = alert_detector
        self.report_generator = report_generator

    async def handle_event(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming Slack events."""
        try:
            event_type = payload.get("type")

            if event_type == "url_verification":
                return {"challenge": payload.get("challenge")}

            elif event_type == "event_callback":
                event = payload.get("event", {})
                return await self._handle_event_callback(event)

            else:
                raise ValueError("Invalid event format")

        except Exception as e:
            logger.error("Error handling Slack event", error=str(e), payload=payload)
            raise

    async def _handle_event_callback(
        self, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle event callback from Slack."""
        event_type = event.get("type")

        if not event_type:
            raise ValueError("Missing event type")

        if event_type == "message":
            await self._handle_message_event(event)
        elif event_type == "app_mention":
            await self.handle_mention(event)
        else:
            logger.debug("Unhandled event type", event_type=event_type)

        return None

    async def _handle_message_event(self, event: dict[str, Any]) -> None:
        """Handle message events."""
        try:
            # Validate text length
            text = event.get("text", "")
            if len(text.encode("utf-8")) > 40000:
                raise ValueError("Text too long")

            # Check if this could be an OOM alert
            alert = await self.alert_detector.detect_oom_alert(event)
            if alert:
                await self.process_oom_alert(alert)

        except Exception as e:
            logger.error("Error handling message event", error=str(e), event=event)
            raise

    async def process_oom_alert(self, alert: OOMAlert) -> None:
        """Process detected OOM alert."""
        try:
            logger.info(
                "Processing OOM alert", alert_id=alert.message_id, pod=alert.pod_name
            )

            # Generate diagnostic report (simplified for now)
            report = await self.report_generator.generate_report(alert)

            # Post response to Slack thread
            await self.post_response(
                channel=alert.channel_id,
                thread_ts=alert.message_id,
                text=report.format_for_slack(),
            )

            logger.info("OOM alert processed successfully", alert_id=alert.message_id)

        except Exception as e:
            logger.error(
                "Failed to process OOM alert", error=str(e), alert_id=alert.message_id
            )
            # Post error message to thread
            await self.post_response(
                channel=alert.channel_id,
                thread_ts=alert.message_id,
                text=f"❌ Failed to generate diagnostic report: {str(e)}",
            )

    async def handle_mention(self, event: dict[str, Any]) -> None:
        """Handle app mention events."""
        try:
            # Simple help response for mentions
            help_text = (
                "👋 I'm the OOM Diagnostic Bot!\n\n"
                "I automatically monitor this channel for OOM incidents and provide "
                "diagnostic reports.\n"
                "Keywords I watch for: OOMKilled, memory limit exceeded, "
                "OutOfMemoryError\n\n"
                "When I detect an OOM alert, I'll gather information from:\n"
                "• OpenShift/Kubernetes API\n"
                "• Prometheus metrics\n"
                "• CloudWatch logs\n\n"
                "And provide recommendations for resolution."
            )

            await self.post_response(
                channel=event["channel"], thread_ts=event.get("ts"), text=help_text
            )

        except Exception as e:
            logger.error("Error handling mention", error=str(e), event=event)

    async def handle_interactive(self, payload: str) -> dict[str, Any] | None:
        """Handle interactive component events."""
        try:
            payload_dict = json.loads(payload)

            # Validate payload structure
            if "actions" not in payload_dict:
                raise ValueError("Invalid payload format")

            actions = payload_dict["actions"]
            if not actions:
                raise ValueError("Missing action type")

            action = actions[0]
            action_type = action.get("type")

            if not action_type:
                raise ValueError("Missing action type")

            if action_type == "button":
                return await self.handle_button_action(payload_dict)
            elif action_type == "static_select":
                return await self.handle_select_action(payload_dict)
            else:
                logger.warning("Unhandled action type", action_type=action_type)

            return None

        except json.JSONDecodeError:
            raise ValueError("Invalid payload format")
        except Exception as e:
            logger.error("Error handling interactive event", error=str(e))
            raise

    async def handle_interactive_form(self, form_data: str) -> None:
        """Handle form-encoded interactive payloads."""
        payload_json = self.parse_form_payload(form_data)
        await self.handle_interactive(payload_json)

    def parse_form_payload(self, form_data: str) -> str:
        """Parse form-encoded payload."""
        # Extract JSON from form data
        if form_data.startswith("payload="):
            return form_data[8:]  # Remove "payload=" prefix
        return form_data

    async def handle_button_action(
        self, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle button click actions."""
        action = payload["actions"][0]
        action_id = action.get("action_id")

        if action_id == "refresh_report":
            # Handle refresh report button
            logger.info("Refresh report button clicked", user=payload["user"]["id"])
            # TODO: Implement report refresh logic
            pass

        return None

    async def handle_select_action(
        self, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle select menu actions."""
        action = payload["actions"][0]
        action_id = action.get("action_id")

        if action_id == "time_range_select":
            # Handle time range selection
            selected_option = action.get("selected_option", {})
            time_range = selected_option.get("value")
            logger.info(
                "Time range selected", time_range=time_range, user=payload["user"]["id"]
            )
            # TODO: Implement time range filter logic
            pass

        return None

    async def post_response(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> dict[str, Any]:
        """Post response to Slack channel."""
        try:
            response = await self.app.client.chat_postMessage(
                channel=channel, text=text, thread_ts=thread_ts
            )
            return response.data
        except Exception as e:
            logger.error("Failed to post Slack message", error=str(e), channel=channel)
            raise

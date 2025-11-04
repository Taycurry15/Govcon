"""Scheduled discovery runner with Telegram and email notifications."""

from __future__ import annotations

import argparse
import asyncio
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from govcon.agents.discovery import DiscoveryAgent, DiscoveryResult, OpportunitySearchResult
from govcon.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class NotificationConfig:
    """Notification configuration loaded from environment variables."""

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    email_recipients: list[str] | None = None
    email_sender: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True


def parse_args() -> argparse.Namespace:
    """CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run DiscoveryAgent and send Telegram/email notifications."
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=2,
        help="How many days back to search (default: 2).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of opportunities to include in notifications (default: 5).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discovery but skip sending notifications.",
    )
    parser.add_argument(
        "--fallback-days",
        type=int,
        default=30,
        help="If no results are found, rerun discovery with this wider window (default: 30).",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable automatic fallback search when no opportunities are found.",
    )
    return parser.parse_args()


def load_notification_config() -> NotificationConfig:
    """Load notification configuration from environment variables."""
    email_recipients = os.getenv("DISCOVERY_EMAIL_TO")
    recipients_list = [addr.strip() for addr in email_recipients.split(",")] if email_recipients else None

    smtp_port_str = os.getenv("DISCOVERY_EMAIL_SMTP_PORT")
    smtp_port = int(smtp_port_str) if smtp_port_str else None

    use_tls = os.getenv("DISCOVERY_EMAIL_SMTP_USE_TLS", "true").lower() != "false"

    return NotificationConfig(
        telegram_bot_token=os.getenv("DISCOVERY_TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("DISCOVERY_TELEGRAM_CHAT_ID"),
        email_recipients=recipients_list,
        email_sender=os.getenv("DISCOVERY_EMAIL_FROM"),
        smtp_host=os.getenv("DISCOVERY_EMAIL_SMTP_HOST"),
        smtp_port=smtp_port,
        smtp_username=os.getenv("DISCOVERY_EMAIL_SMTP_USERNAME"),
        smtp_password=os.getenv("DISCOVERY_EMAIL_SMTP_PASSWORD"),
        smtp_use_tls=use_tls,
    )


def _sort_opportunities(opps: list[OpportunitySearchResult]) -> list[OpportunitySearchResult]:
    """Sort opportunities by relevance, giving priority to higher match scores, shapeable flag, and earliest deadlines."""

    def key(opp: OpportunitySearchResult) -> tuple[float, int, float]:
        score = max(opp.naics_match, opp.psc_match)
        shapeable = 1 if opp.shapeable else 0
        deadline = opp.response_deadline or datetime.max.replace(tzinfo=timezone.utc)
        # Negate timestamp so earlier deadlines rank higher when reverse sorting.
        return (score, shapeable, -deadline.timestamp())

    return sorted(opps, key=key, reverse=True)


def format_opportunity(opp: OpportunitySearchResult) -> str:
    """Format a single opportunity as a single-line summary."""
    posted = opp.posted_date.strftime("%Y-%m-%d")
    deadline = opp.response_deadline.strftime("%Y-%m-%d") if opp.response_deadline else "N/A"
    naics = opp.naics_code or "N/A"
    set_aside = opp.set_aside or "Unknown"
    score = max(opp.naics_match, opp.psc_match)
    return (
        f"*{opp.title}* ({opp.solicitation_number})\n"
        f"Agency: {opp.agency} | Posted: {posted} | Due: {deadline}\n"
        f"Set-aside: {set_aside} | NAICS: {naics} | Match score: {score:.2f}\n"
        f"URL: {opp.source_url or 'N/A'}"
    )


def format_summary(result: DiscoveryResult, limit: int) -> tuple[str, str]:
    """Create text bodies for Telegram and email."""
    header = (
        f"Discovery run complete.\n"
        f"- Found: {result.opportunities_found}\n"
        f"- Ingested: {result.opportunities_ingested}\n"
        f"- Updated: {result.opportunities_updated}\n"
        f"- Shapeable: {result.opportunities_shapeable}\n"
        f"- Duration: {result.execution_time:.1f}s"
    )

    if result.analysis_summary:
        header += f"\n\n{result.analysis_summary}"

    sorted_opps = _sort_opportunities(result.opportunities)
    lines = [format_opportunity(opp) for opp in sorted_opps[:limit]]
    body = "\n\n".join(lines) if lines else "No opportunities met the filters."

    telegram_text = f"{header}\n\n{body}"

    email_body = (
        f"{header}\n\nHighlighted opportunities (top {min(limit, len(result.opportunities))}):\n\n"
        + "\n\n".join(lines)
    )

    return telegram_text, email_body


def send_telegram_message(token: str, chat_id: str, text: str, reply_markup: dict | None = None) -> None:
    """Send a Telegram message via the Bot API.

    Args:
        token: Telegram bot token
        chat_id: Chat ID to send message to
        text: Message text
        reply_markup: Optional inline keyboard markup
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = httpx.post(url, json={**payload, "parse_mode": "Markdown"}, timeout=10)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Telegram API error (Markdown): %s", exc)
        # Retry without Markdown formatting to avoid entity parsing issues.
        try:
            response = httpx.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram message sent without Markdown formatting due to previous error.")
        except httpx.HTTPError as retry_exc:
            logger.warning("Telegram API error (plain text retry): %s", retry_exc)
    except httpx.HTTPError as exc:
        logger.warning("Telegram API error: %s", exc)


def send_opportunity_with_buttons(token: str, chat_id: str, opp: OpportunitySearchResult) -> None:
    """Send a single opportunity notification with approve/deny buttons.

    Args:
        token: Telegram bot token
        chat_id: Chat ID to send message to
        opp: Opportunity to send
    """
    text = format_opportunity(opp)

    # Create inline keyboard with approve and deny buttons
    inline_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Approve",
                    "callback_data": f"approve:{opp.solicitation_number}"
                },
                {
                    "text": "❌ Deny",
                    "callback_data": f"deny:{opp.solicitation_number}"
                }
            ]
        ]
    }

    send_telegram_message(token, chat_id, text, reply_markup=inline_keyboard)


def send_email(config: NotificationConfig, subject: str, body: str) -> None:
    """Send email notification using SMTP."""
    if not config.email_sender or not config.email_recipients:
        logger.info("Email notification skipped (sender or recipients missing).")
        return

    if not config.smtp_host or not config.smtp_port:
        logger.warning("SMTP host/port not configured; email notification skipped.")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.email_sender
    message["To"] = ", ".join(config.email_recipients)
    message.set_content(body)

    if config.smtp_use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as server:
            server.starttls(context=context)
            if config.smtp_username and config.smtp_password:
                server.login(config.smtp_username, config.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as server:
            if config.smtp_username and config.smtp_password:
                server.login(config.smtp_username, config.smtp_password)
            server.send_message(message)


async def run_discovery(
    *,
    days_back: int,
    set_aside_filter: list[str] | None = None,
    naics_codes: list[str] | None = None,
    psc_codes: list[str] | None = None,
    keywords: list[str] | None = None,
) -> DiscoveryResult:
    """Execute discovery and return the result."""
    agent = DiscoveryAgent()
    return await agent.discover(
        days_back=days_back,
        set_aside_filter=set_aside_filter,
        naics_codes=naics_codes,
        psc_codes=psc_codes,
        keywords=keywords,
    )


def main() -> int:
    """Entrypoint for CLI execution."""
    args = parse_args()
    config = load_notification_config()

    result = asyncio.run(run_discovery(days_back=args.days_back))
    fallback_note = ""

    if not args.no_fallback and result.opportunities_found == 0:
        logger.info(
            "No opportunities found with primary filters. Applying fallback search: days_back=%s (no set-aside/NAICS/PSC filters).",
            args.fallback_days,
        )
        fallback_result = asyncio.run(
            run_discovery(
                days_back=args.fallback_days,
                set_aside_filter=[],
                naics_codes=[],
                psc_codes=[],
                keywords=[],
            )
        )
        if fallback_result.opportunities_found:
            logger.info(
                "Fallback search found %s opportunities (shapeable=%s).",
                fallback_result.opportunities_found,
                fallback_result.opportunities_shapeable,
            )
        else:
            logger.info("Fallback search also returned no opportunities.")
        result = fallback_result
        fallback_note = (
            f"Fallback search applied with days_back={args.fallback_days} and widened filters.\n\n"
        )

    telegram_text, email_body = format_summary(result, args.limit)

    if fallback_note:
        telegram_text = fallback_note + telegram_text
        email_body = fallback_note + email_body

    logger.info("Discovery run complete: found=%s shapeable=%s", result.opportunities_found, result.opportunities_shapeable)

    if args.dry_run:
        logger.info("Dry run enabled. Notifications suppressed.")
        print(telegram_text)
        return 0

    if config.telegram_bot_token and config.telegram_chat_id:
        # Send summary message first
        send_telegram_message(config.telegram_bot_token, config.telegram_chat_id, telegram_text)

        # Send individual opportunity notifications with approve/deny buttons
        sorted_opps = _sort_opportunities(result.opportunities)
        for opp in sorted_opps[:args.limit]:
            try:
                send_opportunity_with_buttons(config.telegram_bot_token, config.telegram_chat_id, opp)
                logger.info(f"Sent opportunity notification with buttons: {opp.solicitation_number}")
            except Exception as exc:
                logger.error(f"Failed to send opportunity {opp.solicitation_number}: {exc}")
    else:
        logger.info("Telegram notification skipped (token or chat ID missing).")

    send_email(config, subject="Discovery pipeline update", body=email_body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

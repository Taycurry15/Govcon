"""Telegram workflow controller for approval and status updates.

This service listens to Telegram bot commands and toggles opportunity approvals.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from sqlalchemy import asc, desc, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from govcon.agents.orchestrator import WorkflowOrchestrator, WorkflowStage  # noqa: E402
from govcon.models.opportunity import Opportunity, OpportunityStatus  # noqa: E402
from govcon.utils.database import get_db  # noqa: E402
from govcon.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def _env(name: str, fallback: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return fallback
    return value


BOT_TOKEN = _env("TELEGRAM_APPROVAL_BOT_TOKEN", _env("DISCOVERY_TELEGRAM_BOT_TOKEN"))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None
POLL_INTERVAL = float(_env("TELEGRAM_APPROVAL_POLL_INTERVAL", "1.5"))
POLL_TIMEOUT = int(_env("TELEGRAM_APPROVAL_POLL_TIMEOUT", "25"))
ALLOWED_CHAT_IDS = {
    chat_id.strip()
    for chat_id in (_env("TELEGRAM_APPROVAL_ALLOWED_CHAT_IDS", "") or "").split(",")
    if chat_id.strip()
}
ALLOWED_USERNAMES = {
    username.strip().lstrip("@").lower()
    for username in (_env("TELEGRAM_APPROVAL_ALLOWED_USERNAMES", "") or "").split(",")
    if username.strip()
}


if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_APPROVAL_BOT_TOKEN or DISCOVERY_TELEGRAM_BOT_TOKEN must be set in the environment."
    )


def send_telegram_message(chat_id: int | str, text: str) -> None:
    """Send a Telegram message to the specified chat."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    with httpx.Client(timeout=10) as client:
        try:
            response = client.post(f"{API_BASE}/sendMessage", json={**payload, "parse_mode": "Markdown"})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Telegram Markdown send failed: %s", exc)
            try:
                response = client.post(f"{API_BASE}/sendMessage", json=payload)
                response.raise_for_status()
            except httpx.HTTPError as retry_exc:  # pragma: no cover - runtime guard
                logger.error("Telegram send failed after retry: %s", retry_exc)
        except httpx.HTTPError as exc:  # pragma: no cover - runtime guard
            logger.error("Telegram send failed: %s", exc)


def _format_status(opp: Opportunity) -> str:
    """Format the current opportunity status for display."""
    lines = [
        f"*{opp.title}* (`{opp.solicitation_number}`)",
        f"Status: `{opp.status.value}`",
        f"Agency: {opp.agency}",
        f"Deadline: {(opp.response_deadline.isoformat() if opp.response_deadline else 'N/A')}",
        "",
        f"Pink team approved: {'✅' if opp.pink_team_approved else '❌'}"
        + (
            f" by {opp.pink_team_approved_by} at {opp.pink_team_approved_at.isoformat()}"
            if opp.pink_team_approved_at
            else ""
        ),
        f"Gold team approved: {'✅' if opp.gold_team_approved else '❌'}"
        + (
            f" by {opp.gold_team_approved_by} at {opp.gold_team_approved_at.isoformat()}"
            if opp.gold_team_approved_at
            else ""
        ),
    ]
    if opp.bid_recommendation:
        lines.append(f"Bid recommendation: `{opp.bid_recommendation}`")
    if opp.notes:
        lines.append("")
        lines.append("_Latest note:_")
        lines.append(opp.notes.splitlines()[-1])
    return "\n".join(lines)


def _find_opportunity(session, solicitation_number: str) -> Optional[Opportunity]:
    exact_query = select(Opportunity).where(
        Opportunity.solicitation_number == solicitation_number
    )
    result = session.execute(exact_query).scalar_one_or_none()
    if result:
        return result

    like_query = select(Opportunity).where(
        Opportunity.solicitation_number.ilike(f"%{solicitation_number}%")
    )
    return session.execute(like_query).scalar_one_or_none()


def _append_note(opp: Opportunity, source: str, content: str) -> None:
    if not content:
        return
    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    note_entry = f"[{timestamp}] {source}: {content}"
    if opp.notes:
        opp.notes = opp.notes + "\n" + note_entry
    else:
        opp.notes = note_entry


def _handle_approve(
    session,
    solicitation_number: str,
    stage: Optional[str],
    note: str,
    actor: str,
) -> tuple[str, Optional[tuple[WorkflowStage, str]]]:
    opp = _find_opportunity(session, solicitation_number)
    if opp is None:
        return f"❗ Opportunity `{solicitation_number}` not found."

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    stage_normalized = (stage or "").lower()

    orchestrator_stage: Optional[WorkflowStage] = None

    if stage_normalized in {"pink", "pink_team"}:
        opp.pink_team_approved = True
        opp.pink_team_approved_by = actor
        opp.pink_team_approved_at = now
        opp.status = OpportunityStatus.AWAITING_GOLD_TEAM
        action = "Pink Team approval recorded"
        orchestrator_stage = WorkflowStage.SOLICITATION_REVIEW
    elif stage_normalized in {"gold", "gold_team"}:
        opp.gold_team_approved = True
        opp.gold_team_approved_by = actor
        opp.gold_team_approved_at = now
        opp.status = OpportunityStatus.APPROVED
        action = "Gold Team approval recorded"
        orchestrator_stage = WorkflowStage.SUBMISSION
    elif stage_normalized in {"bid", "go", "progress"}:
        opp.status = OpportunityStatus.IN_PROGRESS
        action = "Opportunity marked in progress"
        orchestrator_stage = WorkflowStage.SOLICITATION_REVIEW
    else:
        opp.status = OpportunityStatus.IN_PROGRESS
        action = "Opportunity approved for next stage"
        orchestrator_stage = WorkflowStage.SOLICITATION_REVIEW

    note_line = f"Approve {stage_normalized or 'general'}."
    if note:
        note_line += f" Notes: {note}"
    _append_note(opp, f"Telegram @{actor}", note_line)
    logger.info("Opportunity %s: %s by %s", opp.solicitation_number, action, actor)
    message = f"✅ {action} for `{opp.solicitation_number}`."
    if orchestrator_stage is None:
        return message, None
    return message, (orchestrator_stage, opp.id)


def _handle_reject(session, solicitation_number: str, note: str, actor: str) -> str:
    opp = _find_opportunity(session, solicitation_number)
    if opp is None:
        return f"❗ Opportunity `{solicitation_number}` not found."

    opp.status = OpportunityStatus.REJECTED
    opp.pink_team_approved = False
    opp.pink_team_approved_by = None
    opp.pink_team_approved_at = None
    opp.gold_team_approved = False
    opp.gold_team_approved_by = None
    opp.gold_team_approved_at = None
    note_line = "Rejected."
    if note:
        note_line += f" Reason: {note}"
    _append_note(opp, f"Telegram @{actor}", note_line)
    logger.info("Opportunity %s rejected by %s", opp.solicitation_number, actor)
    return f"🛑 Opportunity `{opp.solicitation_number}` marked as rejected."


def _handle_status(session, solicitation_number: str) -> str:
    opp = _find_opportunity(session, solicitation_number)
    if opp is None:
        return f"❗ Opportunity `{solicitation_number}` not found."
    return _format_status(opp)


def _handle_list(session) -> str:
    query = select(Opportunity).order_by(desc(Opportunity.posted_date)).limit(10)
    results = session.execute(query).scalars().all()
    if not results:
        return "No opportunities available."

    lines = ["Latest opportunities:"]
    for opp in results:
        deadline = opp.response_deadline.strftime("%Y-%m-%d") if opp.response_deadline else "N/A"
        lines.append(f"- `{opp.solicitation_number}` | {opp.title[:70]} (Due: {deadline})")
    return "\n".join(lines)


def _handle_search(session, query_text: str) -> str:
    if not query_text:
        return "Provide a search term, e.g. `/search zero trust`."

    like_term = f"%{query_text}%"
    query = (
        select(Opportunity)
        .where(
            Opportunity.solicitation_number.ilike(like_term)
            | Opportunity.title.ilike(like_term)
        )
        .order_by(desc(Opportunity.posted_date))
        .limit(10)
    )
    results = session.execute(query).scalars().all()
    if not results:
        return f"No opportunities found matching `{query_text}`."

    lines = [f"Matches for `{query_text}`:"]
    for opp in results:
        lines.append(f"- `{opp.solicitation_number}` | {opp.title[:70]}")
    return "\n".join(lines)


def _map_status_to_stage(status: OpportunityStatus) -> str:
    mapping = {
        OpportunityStatus.DISCOVERED: "Discovery",
        OpportunityStatus.SCREENING: "Screening (Bid/No-Bid)",
        OpportunityStatus.AWAITING_PINK_TEAM: "Awaiting Pink Team",
        OpportunityStatus.AWAITING_GOLD_TEAM: "Awaiting Gold Team",
        OpportunityStatus.IN_PROGRESS: "Proposal Drafting",
        OpportunityStatus.APPROVED: "Approved for Submission",
        OpportunityStatus.SUBMITTED: "Submitted",
        OpportunityStatus.AWARDED: "Awarded",
        OpportunityStatus.LOST: "Lost",
        OpportunityStatus.WITHDRAWN: "Withdrawn",
        OpportunityStatus.REJECTED: "Rejected",
    }
    return mapping.get(status, status.value.replace("_", " ").title())


def _handle_workflow(session, solicitation_number: str) -> str:
    opp = _find_opportunity(session, solicitation_number)
    if opp is None:
        return f"❗ Opportunity `{solicitation_number}` not found."

    stage = _map_status_to_stage(opp.status)
    deadline = opp.response_deadline.strftime("%Y-%m-%d") if opp.response_deadline else "N/A"
    est_value = f"${opp.estimated_value:,.0f}" if opp.estimated_value else "N/A"
    naics = opp.naics_code or "N/A"
    psc = opp.psc_code or "N/A"
    shapeable = "Yes" if opp.shapeable else "No"

    lines = [
        f"*Workflow Snapshot for* `{opp.solicitation_number}`",
        f"Title: {opp.title}",
        f"Agency: {opp.agency}",
        "",
        f"*Current Stage:* {stage}",
        f"Deadline: {deadline}",
        f"Estimated Value: {est_value}",
        f"NAICS / PSC: {naics} / {psc}",
        f"Shapeable Opportunity: {shapeable}",
        "",
        "*Approvals*",
        f"Pink Team: {'✅' if opp.pink_team_approved else '❌'}"
        + (
            f" (by {opp.pink_team_approved_by} at {opp.pink_team_approved_at.strftime('%Y-%m-%d %H:%M')})"
            if opp.pink_team_approved_at
            else ""
        ),
        f"Gold Team: {'✅' if opp.gold_team_approved else '❌'}"
        + (
            f" (by {opp.gold_team_approved_by} at {opp.gold_team_approved_at.strftime('%Y-%m-%d %H:%M')})"
            if opp.gold_team_approved_at
            else ""
        ),
    ]

    if opp.bid_recommendation or opp.bid_score_total is not None:
        lines.append("")
        lines.append("*Bid/No-Bid Summary*")
        if opp.bid_recommendation:
            lines.append(f"Recommendation: `{opp.bid_recommendation}`")
        if opp.bid_score_total is not None:
            lines.append(f"Total Score: {opp.bid_score_total:.1f}")

    if opp.notes:
        recent_note = opp.notes.splitlines()[-1]
        lines.append("")
        lines.append(f"_Latest Note:_ {recent_note}")

    next_steps = []
    if not opp.pink_team_approved and opp.status in {
        OpportunityStatus.SCREENING,
        OpportunityStatus.AWAITING_PINK_TEAM,
    }:
        next_steps.append("Pink Team approval pending.")
    if opp.pink_team_approved and not opp.gold_team_approved and opp.status in {
        OpportunityStatus.AWAITING_GOLD_TEAM,
        OpportunityStatus.IN_PROGRESS,
    }:
        next_steps.append("Gold Team approval pending.")
    if opp.gold_team_approved and opp.status in {
        OpportunityStatus.IN_PROGRESS,
        OpportunityStatus.APPROVED,
    }:
        next_steps.append("Prepare final submission package.")

    if next_steps:
        lines.append("")
        lines.append("*Next Steps*")
        for step in next_steps:
            lines.append(f"- {step}")

    return "\n".join(lines)


def _handle_pipeline_overview(session) -> str:
    tracked_statuses = [
        OpportunityStatus.AWAITING_PINK_TEAM,
        OpportunityStatus.AWAITING_GOLD_TEAM,
        OpportunityStatus.IN_PROGRESS,
        OpportunityStatus.APPROVED,
        OpportunityStatus.SUBMITTED,
    ]

    query = (
        select(Opportunity)
        .where(Opportunity.status.in_(tracked_statuses))
        .order_by(asc(Opportunity.status), asc(Opportunity.response_deadline))
    )
    results = session.execute(query).scalars().all()
    if not results:
        return "No in-flight opportunities at the moment."

    lines = ["*Pipeline Overview*"]
    for opp in results:
        stage = _map_status_to_stage(opp.status)
        deadline = opp.response_deadline.strftime("%Y-%m-%d") if opp.response_deadline else "N/A"
        lines.append(
            f"- `{opp.solicitation_number}` | {stage} | Due: {deadline} | Pink: {'✅' if opp.pink_team_approved else '❌'} | Gold: {'✅' if opp.gold_team_approved else '❌'}"
        )
    lines.append("")
    lines.append("Use `/workflow <solicitation>` for detailed context.")
    return "\n".join(lines)


def _trigger_orchestrator(chat_id: int | str, request: tuple[WorkflowStage, str]) -> None:
    start_stage, opportunity_id = request
    orchestrator = WorkflowOrchestrator()
    try:
        send_telegram_message(
            chat_id,
            f"🤖 Launching orchestrator from `{start_stage.value}` for opportunity `{opportunity_id}`...",
        )

        result = asyncio.run(
            orchestrator.execute_full_workflow(
                opportunity_id=opportunity_id,
                auto_approve=True,
                start_from_stage=start_stage,
            )
        )

        final_stage = result.final_stage
        status_update: Optional[OpportunityStatus] = None
        if final_stage == WorkflowStage.SUBMISSION:
            status_update = OpportunityStatus.SUBMITTED
        elif final_stage == WorkflowStage.GOLD_TEAM:
            status_update = OpportunityStatus.APPROVED
        elif final_stage == WorkflowStage.PRICING:
            status_update = OpportunityStatus.AWAITING_GOLD_TEAM
        elif final_stage == WorkflowStage.PROPOSAL_DRAFTING:
            status_update = OpportunityStatus.IN_PROGRESS

        if status_update is not None:
            with get_db() as session:
                opp = session.get(Opportunity, opportunity_id)
                if opp:
                    opp.status = status_update

        summary = (result.summary or "").strip()
        message_lines = [
            f"✅ Workflow resumed from `{start_stage.value}`.",
            f"Final orchestrator stage: `{final_stage.value}`.",
        ]
        if status_update:
            message_lines.append(f"Opportunity status updated to `{status_update.value}`.")
        if summary:
            message_lines.append("")
            message_lines.append(summary)

        send_telegram_message(chat_id, "\n".join(message_lines))
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Failed to continue orchestrator workflow: %s", exc)
        send_telegram_message(
            chat_id,
            f"⚠️ Unable to run orchestrator continuation: {exc}",
        )


def _handle_reset(session, solicitation_number: str, actor: str) -> str:
    opp = _find_opportunity(session, solicitation_number)
    if opp is None:
        return f"❗ Opportunity `{solicitation_number}` not found."

    opp.status = OpportunityStatus.SCREENING
    opp.pink_team_approved = False
    opp.pink_team_approved_by = None
    opp.pink_team_approved_at = None
    opp.gold_team_approved = False
    opp.gold_team_approved_by = None
    opp.gold_team_approved_at = None
    _append_note(opp, f"Telegram @{actor}", "Reset approvals and status to screening.")
    logger.info("Opportunity %s reset by %s", opp.solicitation_number, actor)
    return f"🔁 Opportunity `{opp.solicitation_number}` reset to screening."


HELP_TEXT = (
    "Available commands:\n"
    "/approve <solicitation> [pink|gold|bid] [note] – Approve and advance workflow.\n"
    "/reject <solicitation> [note] – Mark opportunity as rejected.\n"
    "/status <solicitation> – Display current status and approvals.\n"
    "/workflow <solicitation> – Rich context for a specific opportunity.\n"
    "/pipeline [solicitation] – Overview of in-flight approvals or drill into a specific opportunity.\n"
    "/list – Show 10 most recent opportunities with solicitation numbers.\n"
    "/search <query> – Search opportunities by solicitation number or title.\n"
    "/reset <solicitation> – Reset approvals and status to screening.\n"
    "/help – Show this message."
)


def _is_authorized(chat_id: int | str, username: Optional[str]) -> bool:
    if ALLOWED_CHAT_IDS and str(chat_id) not in ALLOWED_CHAT_IDS:
        return False
    if ALLOWED_USERNAMES and (username or "").lower() not in ALLOWED_USERNAMES:
        return False
    return True


def handle_callback_query(callback_query: dict[str, Any]) -> None:
    """Handle inline keyboard button presses (callback queries)."""
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    user = callback_query.get("from") or {}
    username = (user.get("username") or user.get("first_name") or str(user.get("id", ""))).strip()

    if not _is_authorized(chat_id, user.get("username")):
        logger.warning("Unauthorized Telegram callback from chat %s user %s", chat_id, username)
        # Answer the callback to remove the loading state
        _answer_callback_query(callback_id, "🚫 You are not authorized.")
        return

    # Parse callback data (format: "approve:SOL123" or "deny:SOL123")
    if ":" not in data:
        _answer_callback_query(callback_id, "❗ Invalid button data.")
        return

    action, solicitation_number = data.split(":", 1)

    orchestrator_request: Optional[tuple[WorkflowStage, str]] = None

    with get_db() as session:
        if action == "approve":
            message_text, orchestrator_request = _handle_approve(
                session, solicitation_number, None, f"Approved via button", username
            )
        elif action == "deny":
            message_text = _handle_reject(session, solicitation_number, f"Denied via button", username)
        else:
            message_text = "❗ Unknown action."

    # Answer the callback query to remove the loading state
    _answer_callback_query(callback_id, "Action processed")

    # Send response message
    send_telegram_message(chat_id, message_text)

    # Trigger orchestrator if needed
    if orchestrator_request:
        _trigger_orchestrator(chat_id, orchestrator_request)


def _answer_callback_query(callback_query_id: str, text: str) -> None:
    """Answer a callback query to remove the loading state on the button."""
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
    }

    with httpx.Client(timeout=10) as client:
        try:
            response = client.post(f"{API_BASE}/answerCallbackQuery", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to answer callback query: %s", exc)


def handle_update(update: dict[str, Any]) -> None:
    # Handle callback queries (button presses)
    if "callback_query" in update:
        handle_callback_query(update["callback_query"])
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    user = message.get("from") or {}
    username = (user.get("username") or user.get("first_name") or str(user.get("id", ""))).strip()

    if not _is_authorized(chat_id, user.get("username")):
        logger.warning("Unauthorized Telegram access from chat %s user %s", chat_id, username)
        send_telegram_message(chat_id, "🚫 You are not authorized to control the workflow.")
        return

    text = message.get("text", "").strip()
    if not text.startswith("/"):
        return

    parts = text.split()
    if not parts:
        return

    command = parts[0].split("@")[0].lower()

    def response(msg: str) -> None:
        send_telegram_message(chat_id, msg)

    if command in {"/help", "/start"}:
        response(HELP_TEXT)
        return
    if command == "/pipeline":
        with get_db() as session:
            if len(parts) >= 2:
                response(_handle_workflow(session, parts[1]))
            else:
                response(_handle_pipeline_overview(session))
        return
    if command == "/list":
        with get_db() as session:
            response(_handle_list(session))
        return
    if command == "/search":
        query_text = " ".join(parts[1:]).strip()
        with get_db() as session:
            response(_handle_search(session, query_text))
        return

    if len(parts) < 2:
        response("Usage requires a solicitation number. Try `/help`.")
        return

    solicitation_number = parts[1]
    note_start_index = 2
    stage = None

    if command == "/approve" and len(parts) >= 3 and parts[2].lower() in {"pink", "pink_team", "gold", "gold_team", "bid", "go", "progress"}:
        stage = parts[2]
        note_start_index = 3

    note = " ".join(parts[note_start_index:]).strip()

    orchestrator_request: Optional[tuple[WorkflowStage, str]] = None
    with get_db() as session:
        if command == "/approve":
            message_text, orchestrator_request = _handle_approve(
                session, solicitation_number, stage, note, username
            )
        elif command == "/reject":
            message_text = _handle_reject(session, solicitation_number, note, username)
        elif command == "/status":
            message_text = _handle_status(session, solicitation_number)
        elif command == "/workflow":
            message_text = _handle_workflow(session, solicitation_number)
        elif command == "/reset":
            message_text = _handle_reset(session, solicitation_number, username)
        else:
            message_text = "Unknown command. Use /help to see available commands."

    response(message_text)

    if orchestrator_request:
        _trigger_orchestrator(chat_id, orchestrator_request)


def poll_updates() -> None:
    offset: Optional[int] = None
    logger.info("Starting Telegram workflow controller polling loop.")

    with httpx.Client(timeout=POLL_TIMEOUT + 5) as client:
        while True:
            try:
                params = {"timeout": POLL_TIMEOUT}
                if offset is not None:
                    params["offset"] = offset

                response = client.get(f"{API_BASE}/getUpdates", params=params)
                response.raise_for_status()
                updates = response.json().get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1
                    handle_update(update)

            except httpx.HTTPError as exc:
                logger.error("Telegram polling error: %s", exc)
                time.sleep(POLL_INTERVAL)
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.exception("Unexpected error when processing updates: %s", exc)
                time.sleep(POLL_INTERVAL)

            time.sleep(POLL_INTERVAL)


def main() -> None:
    try:
        poll_updates()
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        logger.info("Telegram workflow controller stopped by user.")


if __name__ == "__main__":
    main()

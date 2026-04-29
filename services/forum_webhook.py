"""
FastAPI router — Telegram webhook for forum monitor inline keyboard callbacks.

Registered at: POST /api/telegram/forum-webhook

Telegram sends a callback_query when the user taps ✓ Use this or ✗ Skip.
callback_data format: "approve:<uuid>" or "skip:<uuid>"

On approve: fetch draft from forum_monitor_queue, send as plain Telegram message for copy-paste.
On skip: mark the row as skipped.

Env vars required:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
"""

import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from supabase import create_client, Client

router = APIRouter(prefix="/api/telegram")

_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
_supabase: Client | None = None


def _get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase = create_client(url, key)
    return _supabase


@router.post("/forum-webhook")
async def forum_webhook(request: Request) -> dict:
    """Handle Telegram callback_query from forum monitor inline keyboard."""
    body = await request.json()

    callback = body.get("callback_query")
    if not callback:
        # Not a callback — could be a regular message update, ignore
        return {"ok": True}

    callback_id = callback.get("id")
    callback_data: str = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id", _chat_id)

    if not callback_data or ":" not in callback_data:
        await _answer_callback(callback_id, "Unknown action")
        return {"ok": True}

    action, queue_id = callback_data.split(":", 1)

    if action == "approve":
        await _handle_approve(callback_id, chat_id, queue_id)
    elif action == "skip":
        await _handle_skip(callback_id, queue_id)
    else:
        await _answer_callback(callback_id, "Unknown action")

    return {"ok": True}


async def _handle_approve(callback_id: str, chat_id: str, queue_id: str) -> None:
    result = (
        _get_supabase().table("forum_monitor_queue")
        .select("thread_title, thread_url, draft_response, product, forum, section")
        .eq("id", queue_id)
        .single()
        .execute()
    )

    if not result.data:
        await _answer_callback(callback_id, "Thread not found")
        return

    row = result.data

    # Update status
    _get_supabase().table("forum_monitor_queue").update({"status": "approved"}).eq("id", queue_id).execute()

    # Send the draft as a plain copyable message
    text = (
        f"*{row['forum']} — {row['section']}*\n"
        f"{row['thread_url']}\n\n"
        f"*Draft to post:*\n\n"
        f"{row['draft_response']}"
    )

    await _send_message(str(chat_id), text)
    await _answer_callback(callback_id, "Draft sent — copy and paste above")


async def _handle_skip(callback_id: str, queue_id: str) -> None:
    _get_supabase().table("forum_monitor_queue").update({"status": "skipped"}).eq("id", queue_id).execute()
    await _answer_callback(callback_id, "Skipped")


async def _answer_callback(callback_id: str, text: str) -> None:
    """Acknowledge the callback query (required by Telegram within 10s)."""
    if not _bot_token or not callback_id:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{_bot_token}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=5,
        )


async def _send_message(chat_id: str, text: str) -> None:
    if not _bot_token:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{_bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )

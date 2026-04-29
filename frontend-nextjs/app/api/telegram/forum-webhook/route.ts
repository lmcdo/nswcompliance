/**
 * POST /api/telegram/forum-webhook
 *
 * Telegram sends a callback_query when the user taps ✓ Use this or ✗ Skip
 * on a forum monitor alert. callback_data format: "approve:<uuid>" | "skip:<uuid>"
 *
 * On approve: fetch draft from forum_monitor_queue, send as plain message for copy-paste.
 * On skip: mark row as skipped.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN ?? '';

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );
}

async function answerCallback(callbackId: string, text: string) {
  if (!BOT_TOKEN || !callbackId) return;
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ callback_query_id: callbackId, text }),
  });
}

async function sendMessage(chatId: string, text: string) {
  if (!BOT_TOKEN) return;
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  });
}

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: true });
  }

  const callback = body.callback_query as Record<string, unknown> | undefined;
  if (!callback) return NextResponse.json({ ok: true });

  const callbackId = String(callback.id ?? '');
  const callbackData = String(callback.data ?? '');
  const chatId = String(
    (callback.message as Record<string, unknown> | undefined)?.chat
      ? ((callback.message as Record<string, unknown>).chat as Record<string, unknown>).id
      : process.env.TELEGRAM_CHAT_ID ?? '',
  );

  if (!callbackData || !callbackData.includes(':')) {
    await answerCallback(callbackId, 'Unknown action');
    return NextResponse.json({ ok: true });
  }

  const colonIdx = callbackData.indexOf(':');
  const action = callbackData.slice(0, colonIdx);
  const queueId = callbackData.slice(colonIdx + 1);

  const supabase = getSupabase();

  if (action === 'approve') {
    const { data: row } = await supabase
      .from('forum_monitor_queue')
      .select('thread_title, thread_url, draft_response, product, forum, section')
      .eq('id', queueId)
      .single();

    if (!row) {
      await answerCallback(callbackId, 'Thread not found');
      return NextResponse.json({ ok: true });
    }

    await supabase
      .from('forum_monitor_queue')
      .update({ status: 'approved' })
      .eq('id', queueId);

    const text =
      `*${row.forum} \u2014 ${row.section}*\n` +
      `${row.thread_url}\n\n` +
      `*Draft to post:*\n\n` +
      `${row.draft_response}`;

    await sendMessage(chatId, text);
    await answerCallback(callbackId, 'Draft sent \u2014 copy and paste above');

  } else if (action === 'skip') {
    await supabase
      .from('forum_monitor_queue')
      .update({ status: 'skipped' })
      .eq('id', queueId);

    await answerCallback(callbackId, 'Skipped');

  } else {
    await answerCallback(callbackId, 'Unknown action');
  }

  return NextResponse.json({ ok: true });
}

/**
 * GET /api/intelligence-brief/stream?runId=xxx
 *
 * Server-side SSE proxy to Trigger.dev Realtime Streams API.
 * Connects to the intelligence-brief stream for a given run and
 * forwards events to the browser as standard SSE.
 *
 * Why a proxy? The @trigger.dev/react-hooks package crashes the
 * Next.js client bundle (hydration failure). Using a server-side
 * proxy with native EventSource on the client avoids this entirely.
 */

import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 120; // Brief generation takes ~70s

const TRIGGER_API_BASE = 'https://api.trigger.dev';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;
const STREAM_KEY = 'intelligence-brief';

export async function GET(request: NextRequest) {
  const runId = request.nextUrl.searchParams.get('runId');
  if (!runId) {
    return new Response('runId is required', { status: 400 });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const sendEvent = (event: string, data: unknown) => {
        controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
      };

      // Connect to the run shape stream to get status updates and detect stream availability
      const runUrl = `${TRIGGER_API_BASE}/realtime/v1/runs/${runId}`;
      const streamUrl = `${TRIGGER_API_BASE}/realtime/v1/streams/${runId}/${STREAM_KEY}`;

      let streamConnected = false;
      let runFinished = false;
      const abortController = new AbortController();

      // Handle client disconnect
      request.signal.addEventListener('abort', () => {
        abortController.abort();
      });

      // Start polling for stream data with retry
      const connectToStream = async () => {
        let retries = 0;
        const maxRetries = 30; // 30 retries × 2s = 60s max wait

        while (!streamConnected && !abortController.signal.aborted && retries < maxRetries) {
          try {
            console.log('[stream-proxy] attempt %d: fetching %s', retries + 1, streamUrl);
            const resp = await fetch(streamUrl, {
              headers: {
                'Accept': 'text/event-stream',
                'Authorization': `Bearer ${TRIGGER_SECRET}`,
              },
              signal: abortController.signal,
            });

            console.log('[stream-proxy] response: %d %s', resp.status, resp.statusText);
            console.log('[stream-proxy] headers: %s', JSON.stringify(Object.fromEntries(resp.headers.entries())));

            if (!resp.ok) {
              if (resp.status === 404 || resp.status === 400) {
                const errBody = await resp.text().catch(() => '');
                console.log('[stream-proxy] not ready (status %d): %s', resp.status, errBody.substring(0, 200));
                retries++;
                await new Promise(r => setTimeout(r, 2000));
                continue;
              }
              sendEvent('error', { message: `Stream error: HTTP ${resp.status}` });
              controller.close();
              return;
            }

            streamConnected = true;
            sendEvent('connected', { runId, streamKey: STREAM_KEY });

            if (!resp.body) {
              sendEvent('error', { message: 'No response body from stream' });
              controller.close();
              return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });

              // SSE events are separated by double newlines
              const parts = buffer.split('\n\n');
              buffer = parts.pop() ?? '';

              for (const part of parts) {
                if (!part.trim()) continue;

                // Extract data lines (skip id:, event:, and : ping keepalives)
                const lines = part.split('\n');
                let eventData = '';

                for (const line of lines) {
                  if (line.startsWith('data:')) {
                    eventData += line.slice(5).trim();
                  }
                }

                if (!eventData) continue;

                try {
                  // Trigger.dev stream data is double-encoded:
                  // Wire: data: "{\"event\":\"section\",...}"
                  // First JSON.parse → string: '{"event":"section",...}'
                  // Second JSON.parse → object: {event:"section",...}
                  let parsed = JSON.parse(eventData);
                  if (typeof parsed === 'string') {
                    parsed = JSON.parse(parsed);
                  }

                  // v2 batch format
                  if (parsed.records) {
                    for (const record of parsed.records) {
                      let body = typeof record.body === 'string' ? JSON.parse(record.body) : record.body;
                      if (typeof body === 'string') body = JSON.parse(body);
                      sendEvent('chunk', body);
                    }
                  } else {
                    sendEvent('chunk', parsed);
                  }
                } catch {
                  // Skip unparseable data (e.g. keepalive pings)
                }
              }
            }

            // Stream ended normally
            sendEvent('done', { runId });
            controller.close();
            return;

          } catch (err: unknown) {
            if (abortController.signal.aborted) return;
            const msg = err instanceof Error ? err.message : String(err);
            if (retries < maxRetries - 1) {
              retries++;
              await new Promise(r => setTimeout(r, 2000));
            } else {
              sendEvent('error', { message: `Stream connection failed after ${maxRetries} retries: ${msg}` });
              controller.close();
              return;
            }
          }
        }

        if (!streamConnected && !abortController.signal.aborted) {
          sendEvent('error', { message: 'Stream not available — task may not have started' });
          controller.close();
        }
      };

      const pollRunStatus = async () => {
        while (!runFinished && !abortController.signal.aborted) {
          try {
            const resp = await fetch(`${TRIGGER_API_BASE}/api/v3/runs/${runId}`, {
              headers: { 'Authorization': `Bearer ${TRIGGER_SECRET}` },
              signal: abortController.signal,
            });
            if (resp.ok) {
              const run = await resp.json();
              console.log('[stream-proxy] run status: %s finished: %s', run.status, run.finishedAt ?? 'no');
              sendEvent('run_status', { status: run.status, finishedAt: run.finishedAt });
              if (run.status === 'FAILED' || run.status === 'CANCELED' || run.status === 'CRASHED') {
                runFinished = true;
                if (!streamConnected) {
                  sendEvent('error', { message: `Task ${run.status.toLowerCase()}` });
                  controller.close();
                  abortController.abort();
                }
                return;
              }
              if (run.finishedAt) {
                runFinished = true;
                return;
              }
            }
          } catch {
            // Ignore poll errors
          }
          await new Promise(r => setTimeout(r, 3000));
        }
      };

      // Run both in parallel
      await Promise.all([
        connectToStream(),
        pollRunStatus(),
      ]).catch(() => {
        if (!abortController.signal.aborted) {
          try { controller.close(); } catch { /* already closed */ }
        }
      });
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

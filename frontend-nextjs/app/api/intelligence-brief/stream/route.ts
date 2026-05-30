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
            const resp = await fetch(streamUrl, {
              headers: {
                'Accept': 'text/event-stream',
                'Authorization': `Bearer ${TRIGGER_SECRET}`,
              },
              signal: abortController.signal,
            });

            if (!resp.ok) {
              // Stream not ready yet — task hasn't started writing
              if (resp.status === 404 || resp.status === 400) {
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

            // Parse SSE from Trigger.dev and forward to client
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });

              // Parse SSE format: events are separated by double newlines
              const parts = buffer.split('\n\n');
              buffer = parts.pop() ?? '';

              for (const part of parts) {
                if (!part.trim()) continue;

                // Extract data from SSE lines
                const lines = part.split('\n');
                let eventData = '';

                for (const line of lines) {
                  if (line.startsWith('data:')) {
                    eventData += line.slice(5).trim();
                  }
                }

                if (eventData) {
                  try {
                    // Trigger.dev v2 stream format: the data contains the actual chunk
                    const parsed = JSON.parse(eventData);

                    // v2 format wraps in records/batch
                    if (parsed.records) {
                      for (const record of parsed.records) {
                        const body = typeof record.body === 'string' ? JSON.parse(record.body) : record.body;
                        sendEvent('chunk', body);
                      }
                    } else {
                      // v1 format: data is the chunk directly
                      sendEvent('chunk', parsed);
                    }
                  } catch {
                    // Forward raw data if JSON parse fails
                    sendEvent('raw', { data: eventData });
                  }
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

      // Also poll run status to detect failures
      const pollRunStatus = async () => {
        while (!runFinished && !abortController.signal.aborted) {
          try {
            const resp = await fetch(`${TRIGGER_API_BASE}/api/v3/runs/${runId}`, {
              headers: { 'Authorization': `Bearer ${TRIGGER_SECRET}` },
              signal: abortController.signal,
            });
            if (resp.ok) {
              const run = await resp.json();
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

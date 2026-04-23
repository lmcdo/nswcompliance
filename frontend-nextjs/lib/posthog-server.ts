import { PostHog } from 'posthog-node'

let _client: PostHog | null = null

function getClient(): PostHog | null {
  if (process.env.NODE_ENV === 'test') return null

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  if (!key) return null

  if (!_client) {
    _client = new PostHog(key, {
      host: 'https://us.i.posthog.com',
      flushAt: 1,
      flushInterval: 0,
    })
  }
  return _client
}

/**
 * Capture any server-side event to PostHog.
 * Safe to call anywhere — no-ops if key is missing or in test env.
 */
export function captureServerEvent(
  event: string,
  properties: Record<string, unknown> = {},
  distinctId = 'server'
): void {
  const client = getClient()
  if (!client) return
  client.capture({ distinctId, event, properties })
}

/**
 * Capture a server-side exception to PostHog.
 * Safe to call in any API route catch block — no-ops if key is missing or in test env.
 */
export function captureServerException(
  error: unknown,
  context: { endpoint: string; [key: string]: unknown }
): void {
  const client = getClient()
  if (!client) return

  const err = error instanceof Error ? error : new Error(String(error))

  client.capture({
    distinctId: 'server',
    event: '$exception',
    properties: {
      $exception_message: err.message,
      $exception_type: err.constructor?.name ?? 'Error',
      $exception_stack_trace_raw: err.stack,
      ...context,
    },
  })
}

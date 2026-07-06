'use client'

import posthog from 'posthog-js'
import { PostHogProvider as OriginalPostHogProvider } from 'posthog-js/react'

// Only load analytics on real production hosts. Vercel preview deployments
// (*.vercel.app) build with NODE_ENV='production', so a NODE_ENV check does
// NOT exclude them — they capture into the production PostHog project and
// pollute every insight (pageviews, funnels, tool_run counts). Gate on the
// actual hostname instead so only live domains send events.
function isAnalyticsHost(): boolean {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  if (host === 'localhost' || host === '127.0.0.1' || host.endsWith('.local')) return false
  if (host.endsWith('.vercel.app')) return false
  return true
}

if (isAnalyticsHost()) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY || 'phc_BwmI39jDeaLPEKYsjMvphVuz6rCfIYxD592NCU0GmrQ', {
    api_host: 'https://us.i.posthog.com',
    person_profiles: 'identified_only',
    capture_pageview: true,
    capture_pageleave: true,
    session_recording: {
      recordCrossOriginIframes: false
    } as any,
    loaded: (posthog) => {
      if (process.env.NODE_ENV === 'development') posthog.debug()
    }
  })
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  return <OriginalPostHogProvider client={posthog}>{children}</OriginalPostHogProvider>
}

export { posthog }

'use client'

import posthog from 'posthog-js'
import { PostHogProvider as OriginalPostHogProvider } from 'posthog-js/react'
import { useEffect } from 'react'

const isProduction = typeof window !== 'undefined' && window.location.hostname === 'verify.plotdetect.com.au'

if (typeof window !== 'undefined') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY || 'phc_BwmI39jDeaLPEKYsjMvphVuz6rCfIYxD592NCU0GmrQ', {
    api_host: 'https://us.i.posthog.com',
    defaults: '2025-05-24',
    person_profiles: 'always',
    opt_out_capturing_by_default: !isProduction,
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

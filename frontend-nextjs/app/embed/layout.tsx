import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { captureServerEvent } from '@/lib/posthog-server'

export const metadata: Metadata = {
  robots: { index: false, follow: false },
}

// Domains that are authorised to embed PlotDetect tools.
// When the partner program launches, registered domains are added here.
// For now: own domains always allowed; unknown domains are logged but not blocked
// (blocking would break the outreach program before partners are registered).
const AUTHORISED_EMBED_DOMAINS = [
  'plotdetect.com.au',
  'www.plotdetect.com.au',
  'canibuildit.com.au',
  'www.canibuildit.com.au',
  'plotdetect.com',
  'www.plotdetect.com',
  'localhost',
  '127.0.0.1',
];

function getEmbedDomain(referer: string | null): string | null {
  if (!referer) return null;
  try {
    return new URL(referer).hostname;
  } catch {
    return null;
  }
}

export default async function EmbedLayout({ children }: { children: React.ReactNode }) {
  const headersList = await headers();
  const referer = headersList.get('referer');
  const domain = getEmbedDomain(referer);

  // Track all embed usage in PostHog — visible in dashboard under embed_request event
  const isAuthorised = !domain || AUTHORISED_EMBED_DOMAINS.includes(domain)
  const tool = headersList.get('x-invoke-path')?.split('/')[2] ?? 'unknown'
  captureServerEvent('embed_request', {
    domain: domain ?? 'direct',
    tool,
    authorised: isAuthorised,
  })
  // TODO: when partner list is active, return 403 for !isAuthorised

  return (
    <div className="bg-white" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {children}
    </div>
  )
}

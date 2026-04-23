import type { Metadata } from 'next'
import { headers } from 'next/headers'

export const metadata: Metadata = {
  robots: { index: false, follow: false },
}

// Domains that are authorised to embed canibuildit tools.
// When the partner program launches, registered domains are added here.
// For now: own domains always allowed; unknown domains are logged but not blocked
// (blocking would break the outreach program before partners are registered).
const AUTHORISED_EMBED_DOMAINS = [
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

  // Log all embed usage for partner monitoring — non-blocking
  if (domain && !AUTHORISED_EMBED_DOMAINS.includes(domain)) {
    console.info(`[embed] External embed from: ${domain}`);
    // TODO: when partner list is active, return 403 for unregistered domains
  }

  return (
    <div className="bg-white" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {children}
    </div>
  )
}

import type { Metadata } from 'next';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://verify.plotdetect.com.au';

/**
 * /share/granny-flat?address=...
 *
 * Lightweight page that exists solely to serve dynamic OG meta tags for
 * social sharing. Crawlers (Facebook, Twitter, LinkedIn) read the meta tags.
 * Browsers are redirected to the actual granny-flat tool page via client-side
 * meta refresh — NOT a server-side 307, which crawlers follow before reading
 * OG tags.
 *
 * This page lives OUTSIDE the (tools) route group to avoid the 'use client'
 * layout that breaks generateMetadata + searchParams on Next.js 14.2.
 */

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
  const params = await searchParams;
  const address = typeof params.address === 'string' ? params.address : undefined;

  if (!address) {
    return {
      title: 'Granny Flat Eligibility Check NSW — Free Instant Check',
      description: 'Can you build a granny flat on your NSW property? Free instant eligibility check under SEPP Housing 2021.',
    };
  }

  const ogImageUrl = `${SITE_URL}/api/og/granny-flat?address=${encodeURIComponent(address)}`;
  const pageUrl = `${SITE_URL}/share/granny-flat?address=${encodeURIComponent(address)}`;
  const title = `Granny Flat Check — ${address}`;
  const description = `Can you build a granny flat at ${address}? Free instant eligibility check under SEPP Housing 2021.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: pageUrl,
      siteName: 'PlotDetect',
      images: [{ url: ogImageUrl, width: 1200, height: 630, alt: `Granny flat eligibility result for ${address}` }],
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [ogImageUrl],
    },
  };
}

export default async function ShareGrannyFlatPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const address = typeof params.address === 'string' ? params.address : undefined;

  // Redirect via JS — crawlers don't execute scripts so they read OG tags.
  // Can't use redirect() (307) or <meta httpEquiv="refresh"> — Next.js converts
  // both into server-side redirects which Facebook follows before reading tags.
  const target = address
    ? `/granny-flat?address=${encodeURIComponent(address)}`
    : '/granny-flat';

  return (
    <div>
      <script dangerouslySetInnerHTML={{ __html: `window.location.replace("${target}")` }} />
      <p style={{ textAlign: 'center', marginTop: '2rem', fontFamily: 'system-ui' }}>
        Redirecting to <a href={target}>granny flat eligibility check</a>...
      </p>
    </div>
  );
}

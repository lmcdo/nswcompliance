'use client';

import Link from 'next/link';
import { trackFunnelCta } from '@/lib/analytics';

/**
 * A Next.js Link that fires a PostHog event on click.
 * Use on marketing/SEO pages to track CTA engagement without
 * converting the entire page to a client component.
 */
export function TrackedLink({
  href,
  page,
  cta,
  className,
  children,
}: {
  href: string;
  page: string;
  cta: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={className}
      onClick={() => trackFunnelCta(page, cta, href)}
    >
      {children}
    </Link>
  );
}

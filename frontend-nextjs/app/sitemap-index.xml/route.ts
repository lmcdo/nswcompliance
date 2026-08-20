/**
 * Sitemap index, served at /sitemap.xml via a beforeFiles rewrite (#929).
 *
 * Next 14's generateSitemaps() emits only the per-cluster files at
 * /sitemap/{id}.xml — it does NOT create an index, so the conventional
 * /sitemap.xml location 404'd while robots.txt advertised it (found
 * 2026-07-23; a cause of the near-zero index coverage). This handler serves
 * the standard sitemapindex XML over the eight cluster files declared in
 * app/sitemap.ts generateSitemaps().
 */
import { NextResponse } from 'next/server';

const BASE = 'https://canibuildit.com.au';
const CLUSTER_COUNT = 8; // keep in sync with generateSitemaps() in app/sitemap.ts

export const dynamic = 'force-static';

export function GET() {
  const entries = Array.from(
    { length: CLUSTER_COUNT },
    (_, i) => `  <sitemap><loc>${BASE}/sitemap/${i}.xml</loc></sitemap>`,
  ).join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries}
</sitemapindex>
`;

  return new NextResponse(xml, {
    headers: { 'Content-Type': 'application/xml' },
  });
}

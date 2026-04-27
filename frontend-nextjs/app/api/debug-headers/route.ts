import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export function GET(req: NextRequest) {
  const relevant = {
    host: req.headers.get('host'),
    'x-forwarded-host': req.headers.get('x-forwarded-host'),
    'x-forwarded-for': req.headers.get('x-forwarded-for'),
    'cf-connecting-ip': req.headers.get('cf-connecting-ip'),
    nexturl_hostname: req.nextUrl.hostname,
    nexturl_href: req.nextUrl.href,
    pathname: req.nextUrl.pathname,
  };
  return NextResponse.json(relevant);
}

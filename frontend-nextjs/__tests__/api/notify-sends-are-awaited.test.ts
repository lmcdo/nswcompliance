/**
 * Every Resend send in an API route must be awaited.
 *
 * On serverless the instance can be frozen the moment the response is
 * returned, cancelling any request still in flight. An unawaited send means
 * the handler's own work commits, the email never goes, and NOTHING reports a
 * problem - which is indistinguishable from working.
 *
 * Found 2026-08-26 by cross-review on one new route, then measured across the
 * codebase: 3 of 8 routes had it. dcp-interest and verify-interest were
 * internal lead alerts. satellite/granny-flat was worse - it emails the
 * CUSTOMER their result and report link, so a cancelled send means someone who
 * asked for a result was never told it was ready.
 *
 * This reads the route files themselves rather than trusting a list, because a
 * list would drift from the routes exactly as the routes drifted from
 * each other.
 */
import fs from 'fs';
import path from 'path';

const API_DIR = path.join(__dirname, '..', '..', 'app', 'api');

function routeFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...routeFiles(full));
    else if (entry.name === 'route.ts') out.push(full);
  }
  return out;
}

/** Strip line and block comments so a commented-out example cannot fail this. */
function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

const SEND = /(\bawait\s+)?[A-Za-z_$][\w$]*\s*\.\s*emails\s*\.\s*send\s*\(/g;

describe('Resend sends in API routes are awaited', () => {
  const files = routeFiles(API_DIR);
  const senders = files.filter((f) =>
    /\.emails\s*\.\s*send\s*\(/.test(stripComments(fs.readFileSync(f, 'utf8'))),
  );

  it('finds the routes that send at all (guards the guard)', () => {
    // If the api directory moved or route.ts was renamed, every assertion
    // below would pass vacuously - which is how a check stops checking.
    expect(files.length).toBeGreaterThan(0);
    expect(senders.length).toBeGreaterThan(0);
  });

  it.each(senders.map((f) => [path.relative(API_DIR, f), f]))(
    '%s awaits every send',
    (_label, file) => {
      const src = stripComments(fs.readFileSync(file as string, 'utf8'));
      const unawaited = [...src.matchAll(SEND)].filter((m) => !m[1]);
      expect(unawaited.map((m) => m[0])).toEqual([]);
    },
  );
});

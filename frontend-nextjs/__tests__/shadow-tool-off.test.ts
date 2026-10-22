/**
 * The shadow tool was turned off 2026-10-22 by the owner.
 *
 * It sold an "ADG solar access" verdict for neighbouring houses, but ADG 4A-1
 * (2 hours of sun) applies to a new apartment building's own apartments and 3F
 * is visual privacy, so the verdict was not a real standard.
 *
 * This keeps it off: nothing may link to the shadow pages, the sitemap must not
 * list them, and the two routes that took new work must refuse with 410.
 * Already-paid orders are still fulfilled by /api/reports/shadow/generate and the
 * 'shadow' branch of /api/stripe/webhook, which this file deliberately leaves alone.
 *
 * @jest-environment node
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.join(__dirname, '..');

// Files allowed to name the shadow routes: the switched-off pages, the paid report page (kept for buyers),
// the paid-order fulfilment path, and the (now unreachable) tool component.
const ALLOWED = [
  'app/reports/shadow/page.tsx',
  'app/reports/shadow/[report_id]/page.tsx',
  'app/(tools)/shadow/[lga-slug]/page.tsx',
  'app/embed/shadow/page.tsx',
  'app/api/reports/shadow/generate/route.ts',
  'app/api/stripe/webhook/route.ts',
  'components/tools/ShadowTool.tsx',
  'app/internal/page.tsx', // owner-only status page: lists /reports/shadow as 'off'
];

function walk(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '.next') continue;
      walk(p, out);
    } else if (/\.(ts|tsx|js|jsx|mdx)$/.test(e.name)) {
      out.push(p);
    }
  }
  return out;
}

// A page route / link, never an /api/... path (those are server calls, not links).
const SHADOW_LINK = /(?<!\/api)(\/reports\/shadow|\/embed\/shadow|\/shadow\/|['"`]\/shadow['"`?#])/;

describe('shadow tool is off', () => {
  it('no file under app/ or components/ links to the shadow pages', () => {
    const offenders: string[] = [];
    for (const dir of ['app', 'components']) {
      for (const file of walk(path.join(ROOT, dir))) {
        const rel = path.relative(ROOT, file).split(path.sep).join('/');
        if (ALLOWED.includes(rel)) continue;
        const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
        lines.forEach((line, i) => {
          if (/^\s*(\/\/|\*|\/\*)/.test(line)) return; // comments are not links
          if (SHADOW_LINK.test(line)) offenders.push(`${rel}:${i + 1}: ${line.trim().slice(0, 120)}`);
        });
      }
    }
    expect(offenders).toEqual([]);
  });

  it('the tool pages 404 and the council page generates nothing (the paid report page stays for buyers)', () => {
    // app/reports/shadow/[report_id] is NOT switched off: it is the link in paid customers' emails.
    for (const rel of ALLOWED.slice(0, 4).filter((r) => !r.includes('[report_id]'))) {
      const src = fs.readFileSync(path.join(ROOT, rel), 'utf8');
      expect(src).toMatch(/notFound\(\)/);
    }
    const lga = fs.readFileSync(path.join(ROOT, ALLOWED[2]), 'utf8');
    expect(lga).toMatch(/generateStaticParams\(\)\s*{\s*return \[\]/);
  });

  it('sitemap output has no /shadow URL in any chunk', async () => {
    const mod = await import('@/app/sitemap');
    const ids = (await mod.generateSitemaps()).map((s: { id: number }) => s.id);
    const urls: string[] = [];
    for (const id of ids) {
      const entries = await mod.default({ id });
      urls.push(...entries.map((e: { url: string }) => e.url));
    }
    expect(urls.length).toBeGreaterThan(0);
    expect(urls.filter((u) => u.includes('/shadow'))).toEqual([]);
  });

  it('next.config.js has no redirect to or from the shadow pages', () => {
    const cfg = fs.readFileSync(path.join(ROOT, 'next.config.js'), 'utf8');
    expect(cfg).not.toMatch(/source:\s*'\/shadow/);
    expect(cfg).not.toMatch(/destination:\s*'[^']*shadow/);
  });

  it.each([
    ['satellite/shadow', '@/app/api/satellite/shadow/route'],
    ['stripe/checkout/shadow', '@/app/api/stripe/checkout/shadow/route'],
  ])('%s refuses with 410', async (_name, modPath) => {
    const mod = await import(modPath);
    for (const method of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']) {
      const res = await mod[method]();
      expect(res.status).toBe(410);
      expect(await res.json()).toEqual({ error: 'The shadow tool has been turned off.' });
    }
  });
});

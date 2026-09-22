import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export const metadata: Metadata = {
  title: 'Internal — All Offerings',
  robots: { index: false, follow: false },
};

// Single source of truth for "where is everything". Owner-facing index of every
// user-reachable route plus status. Update this list when a route ships.
type Status = 'live' | 'beta' | 'built-unlinked' | 'content' | 'dev';

interface Offering {
  path: string;
  title: string;
  note?: string;
  status: Status;
}

interface Group {
  heading: string;
  items: Offering[];
}

const GROUPS: Group[] = [
  {
    heading: 'Core tools',
    items: [
      { path: '/assessment', title: 'Compliance assessment ("can I build it")', status: 'live' },
      { path: '/property', title: 'Property profile', status: 'live' },
      { path: '/prospector', title: 'Prospector — bulk lot search', status: 'live' },
      { path: '/reports', title: 'Reports hub', note: 'links the 8 tools below', status: 'live' },
      { path: '/check', title: 'Quick check', status: 'live' },
      { path: '/pricing', title: 'Pricing', status: 'live' },
    ],
  },
  {
    heading: 'Duplex / upzoning funnel (consumer + builder)',
    items: [
      { path: '/duplex-check', title: 'Duplex checker — ads landing', note: 'verdict-first, no nav; Google Ads target', status: 'live' },
      { path: '/tools/upzoning-check', title: 'Upzoning / duplex checker — SEO tool', status: 'live' },
      { path: '/for/builders', title: 'For builders — pitch page', status: 'live' },
      { path: '/widget-demo/[slug]', title: 'Per-builder white-label demo', note: '20 slugs in lib/widget-partners.ts; noindexed, outreach-only', status: 'live' },
      { path: '/embed/upzoning', title: 'Embeddable duplex checker (iframe)', note: '?ref=<slug>; goes on builder sites', status: 'live' },
      { path: '/api/upzoning', title: 'API — upzoning eligibility', note: 'POST {address}', status: 'live' },
      { path: '/api/canibuildit/lead', title: 'API — lead capture + consent', note: 'qualified duplex referrals → canibuildit_leads', status: 'live' },
    ],
  },
  {
    heading: 'Reports (reachable from /reports)',
    items: [
      { path: '/reports/intelligence-brief', title: 'Property Intelligence Brief', note: 'now linked in hub; 3 B2C services (da_outcome/vg_comparables/strata_lookup) not yet wired', status: 'live' },
      { path: '/reports/intelligence-brief', title: 'Brief LLM overlay (intent chips + plan card)', note: 'DARK: needs NEXT_PUBLIC_BRIEF_LLM_OVERLAY_ENABLED (Vercel) + BRIEF_LLM_OVERLAY_ENABLED (Railway) both true; engine #738/#742, UI this PR', status: 'built-unlinked' },
      { path: '/reports/conveyancing', title: 'Conveyancing report', status: 'live' },
      { path: '/reports/flood', title: 'Flood risk', status: 'live' },
      { path: '/reports/solar-yield', title: 'Solar yield', status: 'live' },
      { path: '/reports/shadow', title: 'Shadow', status: 'live' },
      { path: '/reports/threat-radar', title: 'Threat radar', status: 'live' },
      { path: '/reports/granny-flat', title: 'Granny flat', status: 'live' },
      { path: '/reports/bushfire', title: 'Bushfire', status: 'live' },
      { path: '/reports/pre-da-history', title: 'Pre-DA site history', status: 'live' },
    ],
  },
  {
    heading: 'Content & free pages',
    items: [
      { path: '/canibuildit', title: 'Can I Build It (consumer hub)', status: 'content' },
      { path: '/climate-risk', title: 'Climate risk', status: 'content' },
      { path: '/dcp-browse', title: 'DCP browser', status: 'content' },
      { path: '/planning-standards', title: 'Planning standards', status: 'content' },
      { path: '/open-data', title: 'Open data', status: 'content' },
      { path: '/developers', title: 'Developers / API', status: 'content' },
      { path: '/partner', title: 'Partner', status: 'content' },
      { path: '/blog', title: 'Blog', status: 'content' },
      { path: '/how-it-works', title: 'How it works', status: 'content' },
      { path: '/quick-guide', title: 'Quick guide', status: 'content' },
      { path: '/user-guide', title: 'User guide', status: 'content' },
      { path: '/glossary', title: 'Glossary', status: 'content' },
      { path: '/about', title: 'About', status: 'content' },
      { path: '/contact', title: 'Contact', status: 'content' },
      { path: '/pricing', title: 'Pricing', status: 'content' },
      { path: '/privacy', title: 'Privacy', status: 'content' },
      { path: '/terms', title: 'Terms', status: 'content' },
    ],
  },
  {
    heading: 'Internal ops (owner only)',
    items: [
      { path: '/internal/leads', title: 'Leads — system of record', note: 'qualified duplex referrals + consent audit', status: 'live' },
      { path: '/internal/setback-review', title: 'Setback value review', status: 'live' },
      { path: '/internal/pipeline', title: 'Pipeline status', note: 'live: what needs you, whether each stage is running, how much of the corpus has structured rules. Read from data, not hand-maintained.', status: 'live' },
      { path: '/internal/dcp-review', title: 'DCP review queue', status: 'live' },
    ],
  },
  {
    heading: 'Dev / test (do not link publicly)',
    items: [
      { path: '/test', title: 'test', status: 'dev' },
      { path: '/ui-test', title: 'ui-test', status: 'dev' },
      { path: '/water-demo', title: 'water-demo', status: 'dev' },
      { path: '/simple', title: 'simple', status: 'dev' },
      { path: '/login', title: 'login', status: 'dev' },
    ],
  },
];

const STATUS_STYLE: Record<Status, string> = {
  live: 'bg-green-100 text-green-800',
  beta: 'bg-blue-100 text-blue-800',
  'built-unlinked': 'bg-amber-100 text-amber-800',
  content: 'bg-slate-100 text-slate-700',
  dev: 'bg-rose-100 text-rose-700',
};

export default async function InternalDirectoryPage() {
  // Gate behind login when auth is enabled (same pattern as the reports layout).
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true') {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      redirect('/login');
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold text-slate-900">All offerings — internal index</h1>
        <p className="mt-2 text-sm text-slate-600">
          Every user-reachable route and its status. Owner-facing; not indexed, not in public nav.
          Update <code className="rounded bg-slate-200 px-1">app/internal/page.tsx</code> when a route ships.
        </p>

        <div className="mt-8 space-y-8">
          {GROUPS.map((group) => (
            <section key={group.heading}>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                {group.heading}
              </h2>
              <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
                {group.items.map((item) => (
                  <li key={item.path} className="flex items-center justify-between gap-4 px-4 py-3">
                    <div className="min-w-0">
                      <Link
                        href={item.path}
                        className="font-medium text-blue-700 hover:underline"
                      >
                        {item.title}
                      </Link>
                      <div className="truncate text-xs text-slate-400">
                        {item.path}
                        {item.note ? ` — ${item.note}` : ''}
                      </div>
                    </div>
                    <span
                      className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[item.status]}`}
                    >
                      {item.status}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getAdminClient } from '@/lib/supabase/admin';

export const metadata: Metadata = {
  title: 'Leads — internal',
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

// The leads system of record. Consented PII + the consent audit live in OUR
// Postgres (not a CRM) so the record is owned and append-only; a CRM record is
// mutable and can't serve as consent proof. Read-only for now — status/routing
// come next (ce-lead-qualifier-research-2026-07.md § remaining steps).

interface Qualification {
  timeline?: string | null;
  ownership?: string | null;
  finance?: string | null;
  budget?: string | null;
}
interface Consent {
  version?: string | null;
  wording?: string | null;
  ip?: string | null;
  captured_at?: string | null;
}
interface Lead {
  id: number;
  created_at: string;
  first_name: string | null;
  email: string;
  phone: string | null;
  address: string | null;
  lga_name: string | null;
  eligible: boolean | null;
  interest_type: string | null;
  qualification: Qualification | null;
  consent: Consent | null;
}

const TIMELINE: Record<string, string> = {
  asap: 'ASAP', '1-3m': '1–3mo', '3-6m': '3–6mo', '6-12m': '6–12mo', researching: '12+/researching',
};
const OWNERSHIP: Record<string, string> = { owner: 'Owns', buying: 'Buying', other: 'Agent/other' };
const FINANCE: Record<string, string> = { sorted: 'Finance sorted', looking: 'Looking', cash: 'Cash', 'not-yet': 'Not yet' };
const BUDGET: Record<string, string> = {
  'under-500k': '<$500k', '500-750k': '$500–750k', '750k-1m': '$750k–1M', '1-1.5m': '$1–1.5M', '1.5m-plus': '$1.5M+', unsure: 'Not sure',
};

function label(map: Record<string, string>, v?: string | null): string | null {
  if (!v) return null;
  return map[v] ?? v;
}

function fmtDate(iso: string): string {
  // Fixed AEST-ish display without pulling a tz lib; the stored value is UTC.
  const d = new Date(iso);
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)}Z`;
}

export default async function InternalLeadsPage({
  searchParams,
}: {
  searchParams: Promise<{ key?: string }>;
}) {
  // No login (the magic-link flow was flaky). Instead a simple shared access
  // key. This page holds customer PII, so it is NOT made fully public — set
  // INTERNAL_ACCESS_KEY in the env and open /internal/leads?key=<that value>.
  // Fail-closed: if the key is unset or wrong, the page 404s and never leaks.
  const required = process.env.INTERNAL_ACCESS_KEY;
  const { key } = await searchParams;
  if (!required || key !== required) notFound();

  const service = getAdminClient();
  const { data, error } = await service
    .from('canibuildit_leads')
    .select('id, created_at, first_name, email, phone, address, lga_name, eligible, interest_type, qualification, consent')
    .order('created_at', { ascending: false })
    .limit(500);

  const leads = (data ?? []) as Lead[];
  const referrals = leads.filter((l) => l.interest_type === 'dual-occ-referral');
  const qualified = referrals.filter((l) => l.qualification && (l.qualification.timeline || l.qualification.ownership));
  const consented = referrals.filter((l) => l.consent && l.consent.version);

  return (
    <div className="min-h-screen bg-slate-50 px-6 py-10">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-2xl font-bold text-slate-900">Leads — system of record</h1>
        <p className="mt-2 text-sm text-slate-600">
          Consented PII + consent audit, owned in our DB (not a CRM). Newest first, last 500.
          Not indexed. Read-only — status/routing/HubSpot-sync are the next build steps.
        </p>

        {error && (
          <div className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            Failed to load leads: {error.message}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <Stat label="All leads (all tools)" value={leads.length} />
          <Stat label="Duplex referrals" value={referrals.length} />
          <Stat label="Qualified (timeline/owner given)" value={qualified.length} />
          <Stat label="With consent audit" value={consented.length} />
        </div>

        <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Contact</th>
                <th className="px-3 py-2">Property</th>
                <th className="px-3 py-2">Result</th>
                <th className="px-3 py-2">Qualification</th>
                <th className="px-3 py-2">Consent</th>
                <th className="px-3 py-2">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">No leads yet.</td></tr>
              )}
              {leads.map((l) => {
                const q = l.qualification ?? {};
                const chips = [
                  label(TIMELINE, q.timeline),
                  label(OWNERSHIP, q.ownership),
                  label(FINANCE, q.finance),
                  label(BUDGET, q.budget),
                ].filter(Boolean) as string[];
                const isReferral = l.interest_type === 'dual-occ-referral';
                const resultLabel = isReferral
                  ? (l.eligible ? 'Eligible' : 'Needs checking')
                  : (l.eligible === true ? 'Eligible' : l.eligible === false ? 'Not eligible' : '—');
                return (
                  <tr key={l.id} className="align-top hover:bg-slate-50">
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-slate-500">{fmtDate(l.created_at)}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-slate-800">{l.first_name || '—'}</div>
                      <div className="text-xs text-slate-500">{l.email}</div>
                      {l.phone && <div className="text-xs text-slate-500">{l.phone}</div>}
                    </td>
                    <td className="px-3 py-2">
                      <div className="text-slate-700">{l.address || '—'}</div>
                      {l.lga_name && <div className="text-xs text-slate-400">{l.lga_name}</div>}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        resultLabel === 'Eligible' ? 'bg-green-100 text-green-800'
                        : resultLabel === 'Needs checking' ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-600'}`}>
                        {resultLabel}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {chips.length === 0 ? (
                        <span className="text-xs text-slate-300">—</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {chips.map((c) => (
                            <span key={c} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{c}</span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {l.consent?.version ? (
                        <span
                          className="text-green-700"
                          title={`${l.consent.wording ?? ''}\nIP ${l.consent.ip ?? '?'} · ${l.consent.captured_at ?? ''}`}
                        >
                          ✓ v{l.consent.version}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-xs text-slate-400">{l.interest_type || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

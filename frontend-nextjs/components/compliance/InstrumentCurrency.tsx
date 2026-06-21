'use client';

import { useEffect, useState } from 'react';

interface CurrencyRow {
  instrument_key: string;
  instrument_label: string;
  instrument_type: string;
  verified_at: string | null;
  version_label: string | null;
  source_url: string | null;
  needs_review: boolean;
}

interface Props {
  council: string;
}

function daysSince(iso: string | null): number | null {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

function statusDot(days: number | null): { color: string; title: string } {
  if (days == null) return { color: 'bg-stone-300', title: 'Not yet verified' };
  if (days <= 14) return { color: 'bg-green-500', title: `Verified ${days}d ago` };
  if (days <= 60) return { color: 'bg-amber-400', title: `Verified ${days}d ago` };
  return { color: 'bg-red-500', title: `Verified ${days}d ago — may be stale` };
}

// Fail-closed: an instrument the monitor has flagged as amended (needs_review)
// can NEVER show as verified/current — it overrides the freshness colour with an
// "under review" warning until a human reconciles it.
function statusFor(row: CurrencyRow): { color: string; title: string; underReview: boolean } {
  if (row.needs_review) {
    return { color: 'bg-amber-500', title: 'Change found at source — under review', underReview: true };
  }
  return { ...statusDot(daysSince(row.verified_at)), underReview: false };
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Not verified';
  return new Date(iso).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function InstrumentCurrency({ council }: Props) {
  const [rows, setRows] = useState<CurrencyRow[] | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!council) return;
    fetch(`/api/instrument-currency?council=${encodeURIComponent(council)}`)
      .then((r) => r.json())
      .then((data) => setRows(data.currency ?? []))
      .catch(() => setRows([]));
  }, [council]);

  if (!rows) return null;
  if (rows.length === 0) return null;

  // Overall status: any instrument under review wins (fail closed); otherwise
  // the worst freshness across instruments.
  const anyReview = rows.some((r) => r.needs_review);
  const worst = rows.reduce<number | null>((acc, row) => {
    const d = daysSince(row.verified_at);
    if (d == null) return acc; // treat null as unknown, not worst
    return acc == null ? d : Math.max(acc, d);
  }, null);
  const overall = anyReview
    ? { color: 'bg-amber-500', title: 'Change found at source — under review' }
    : statusDot(worst);

  const dcpRows = rows.filter((r) => r.instrument_type === 'dcp');
  const stateRows = rows.filter((r) => r.instrument_type !== 'dcp');

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-xs text-stone-500 hover:text-stone-700 w-full text-left"
      >
        <span
          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${overall.color}`}
          title={overall.title}
        />
        <span>Data currency</span>
        <span className="ml-auto">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 text-xs text-stone-600 space-y-3 border-t border-stone-200 pt-2">
          {dcpRows.length > 0 && (
            <div>
              <p className="font-medium text-stone-500 uppercase tracking-wide text-[10px] mb-1">DCP</p>
              {dcpRows.map((row) => {
                const s = statusFor(row);
                return (
                  <div key={row.instrument_key} className="flex items-start gap-1.5 mb-1">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mt-0.5 flex-shrink-0 ${s.color}`} />
                    <span className="flex-1">
                      {row.instrument_label}
                      {s.underReview ? (
                        <span className="text-amber-600 ml-1">— change found at source, under review</span>
                      ) : (
                        <span className="text-stone-400 ml-1">— {formatDate(row.verified_at)}</span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {stateRows.length > 0 && (
            <div>
              <p className="font-medium text-stone-500 uppercase tracking-wide text-[10px] mb-1">State instruments</p>
              {stateRows.map((row) => {
                const s = statusFor(row);
                return (
                  <div key={row.instrument_key} className="flex items-start gap-1.5 mb-1">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mt-0.5 flex-shrink-0 ${s.color}`} />
                    <span className="flex-1">
                      {row.source_url ? (
                        <a
                          href={row.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline hover:text-stone-800"
                        >
                          {row.instrument_label}
                        </a>
                      ) : (
                        row.instrument_label
                      )}
                      {s.underReview ? (
                        // Suppress the stale version/date — they describe the
                        // superseded version that's now under review.
                        <span className="text-amber-600 ml-1">— change found at source, under review</span>
                      ) : (
                        <>
                          {row.version_label && (
                            <span className="text-stone-400 ml-1">({row.version_label})</span>
                          )}
                          <span className="text-stone-400 ml-1">— {formatDate(row.verified_at)}</span>
                        </>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          <p className="text-[10px] text-stone-400 italic leading-tight">
            Verified = last confirmed match to source. Not a guarantee of currency.
            Always check council and legislation.nsw.gov.au before issuing advice.
          </p>
        </div>
      )}
    </div>
  );
}

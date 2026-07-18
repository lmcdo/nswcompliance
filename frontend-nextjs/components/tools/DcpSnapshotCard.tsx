'use client';

// prior-art-checked: display-only consumer of the existing
// /api/dcp/structured-controls route (the Verify assessment DCP tab's data
// source) — no new extraction, no new queries; renders ONLY
// data_status==='numeric' rows (fail-closed, mirrors the route's own
// under_review quarantine). The uncovered-state email capture posts to the
// existing canibuildit lead route under a distinct interest type.

import { useEffect, useState } from 'react';
import posthog from 'posthog-js';

interface Control {
  control_type: string;
  control_label: string;
  direction: 'min' | 'max';
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  section_ref: string | null;
  data_status: 'numeric' | 'not_applicable' | 'under_review';
}

interface Category {
  category: string;
  controls: Control[];
}

function controlValue(c: Control): string | null {
  if (c.value_min != null && c.value_max != null && c.value_min !== c.value_max) {
    return `${c.value_min}–${c.value_max} ${c.unit ?? ''}`.trim();
  }
  const v = c.value_min ?? c.value_max;
  if (v == null) return null;
  const sign = c.direction === 'max' ? '≤' : '≥';
  return `${sign} ${v}${c.unit === '%' ? '%' : c.unit ? ` ${c.unit}` : ''}`;
}

/**
 * Shown under an eligible duplex verdict. Covered council → the numeric DCP
 * standards a DA would be measured against, each cited to its section.
 * Uncovered council → capture the request so extraction demand is ranked by
 * real interest (interest_type 'lga-request' in canibuildit_leads).
 */
export function DcpSnapshotCard({ lgaName }: { lgaName: string }) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [covered, setCovered] = useState<boolean | null>(null);
  const [email, setEmail] = useState('');
  const [requested, setRequested] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(
      `/api/dcp/structured-controls?council=${encodeURIComponent(lgaName)}&dev_type=dual_occupancy`,
    )
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        const cats: Category[] = (data?.categories ?? [])
          .map((cat: Category) => ({
            ...cat,
            controls: cat.controls.filter(
              (c) => c.data_status === 'numeric' && controlValue(c) !== null,
            ),
          }))
          .filter((cat: Category) => cat.controls.length > 0);
        const isCovered = Boolean(data?.has_controls) && cats.length > 0;
        setCovered(isCovered);
        setCategories(isCovered ? cats : null);
        posthog.capture('dcp_snapshot_view', {
          tool: 'duplex-check',
          lga: lgaName,
          covered: isCovered,
        });
      })
      .catch(() => {
        // Fetch failure = unknown coverage. Render nothing — never an
        // uncovered pitch (which would be a wrong claim about our own data).
        if (!cancelled) setCovered(null);
      });
    return () => {
      cancelled = true;
    };
  }, [lgaName]);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    try {
      await fetch('/api/canibuildit/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          lga_name: lgaName,
          interest_type: 'lga-request',
        }),
      });
    } catch {
      /* silent — never block the page */
    }
    posthog.capture('lga_request_submitted', {
      tool: 'duplex-check',
      lga: lgaName,
    });
    setRequested(true);
  };

  if (covered == null) return null;

  if (!covered) {
    if (requested) {
      return (
        <div className="rounded-xl border border-teal-200 bg-teal-50 p-4">
          <p className="text-sm text-teal-800">
            Noted — we&apos;ll email you when {lgaName}&apos;s rulebook is
            loaded.
          </p>
        </div>
      );
    }
    return (
      <div className="rounded-xl border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-900">
          We haven&apos;t loaded {lgaName}&apos;s duplex rulebook yet.
        </p>
        <p className="text-xs text-gray-500 mt-1 mb-2">
          Want the exact numbers your council would measure a DA against? Leave
          your email and we&apos;ll tell you when they&apos;re in.
        </p>
        <form onSubmit={handleRequest} className="flex gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@email.com"
            className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors whitespace-nowrap"
          >
            Tell me when
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 p-4">
      <p className="text-sm font-semibold text-gray-900">
        What a DA here gets measured against
      </p>
      <p className="text-xs text-gray-500 mt-0.5 mb-2">
        {lgaName}&apos;s own development control plan — extracted numbers,
        each cited to its section.
      </p>
      <div className="space-y-1">
        {categories!
          .flatMap((cat) => cat.controls)
          .slice(0, 6)
          .map((c) => {
            const v = controlValue(c);
            return (
              <div
                key={`${c.control_type}-${c.section_ref}`}
                className="flex items-baseline justify-between gap-3 text-sm"
              >
                <span className="text-gray-700">{c.control_label}</span>
                <span className="text-gray-900 font-medium tabular-nums whitespace-nowrap">
                  {v}
                  {c.section_ref && (
                    <span className="ml-1.5 text-[10px] font-normal text-gray-400">
                      {c.section_ref}
                    </span>
                  )}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}

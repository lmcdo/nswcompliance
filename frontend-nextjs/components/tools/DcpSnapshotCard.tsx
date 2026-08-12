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
  // The text that says WHICH case this number is for: "2 bedrooms",
  // "visitor parking", "lots up to 12.5m in width", "R3 zone". The API has
  // always sent it (structured-controls/route.ts:243) and this interface did
  // not declare it, so it was dropped here. Without it a council with four
  // correct parking rates renders as four identical labels holding 1, 1.5, 2
  // and 0.25, and the reader cannot tell which line is theirs.
  condition: string | null;
  data_status: 'numeric' | 'not_applicable' | 'under_review';
}

interface Category {
  category: string;
  controls: Control[];
}

// This is a snapshot card under a verdict, not the full controls table, so a
// cap is legitimate. What was not legitimate was applying it silently.
const SNAPSHOT_LIMIT = 6;

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
export function DcpSnapshotCard({
  lgaName,
  councilSlug,
}: {
  lgaName: string;
  /** dcp_setback_controls slug from the engine (former council for Inner
   *  West); falls back to lgaName when the backend doesn't send one yet. */
  councilSlug?: string | null;
}) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [covered, setCovered] = useState<boolean | null>(null);
  const [general, setGeneral] = useState(false);
  const [email, setEmail] = useState('');
  const [requested, setRequested] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const council = councilSlug || lgaName;

    const fetchControls = async (devType: string): Promise<Category[]> => {
      const r = await fetch(
        `/api/dcp/structured-controls?council=${encodeURIComponent(council)}&dev_type=${devType}`,
      );
      if (!r.ok) throw new Error(String(r.status));
      const data = await r.json();
      if (!data?.has_controls) return [];
      return (data.categories ?? [])
        .map((cat: Category) => ({
          ...cat,
          controls: cat.controls.filter(
            (c: Control) => c.data_status === 'numeric' && controlValue(c) !== null,
          ),
        }))
        .filter((cat: Category) => cat.controls.length > 0);
    };

    (async () => {
      try {
        // Duplex-specific controls first; else the controls that apply to ALL
        // residential development (universal_residential is definitionally
        // applicable — never borrow another dev type's chapter).
        let cats = await fetchControls('dual_occupancy');
        let isGeneral = false;
        if (cats.length === 0) {
          cats = await fetchControls('universal_residential');
          isGeneral = cats.length > 0;
        }
        if (cancelled) return;
        // A single obscure control (e.g. just "solar access hours") reads as
        // thin and undermines trust — below 3 numeric rows, offer the
        // request capture instead of a sparse card.
        const numericCount = cats.reduce((n, c) => n + c.controls.length, 0);
        const isCovered = numericCount >= 3;
        setCovered(isCovered);
        setGeneral(isGeneral);
        setCategories(isCovered ? cats : null);
        posthog.capture('dcp_snapshot_view', {
          tool: 'duplex-check',
          lga: lgaName,
          council,
          covered: isCovered,
          general: isGeneral,
        });
      } catch {
        // Fetch failure = unknown coverage. Render nothing — never an
        // uncovered pitch (which would be a wrong claim about our own data).
        if (!cancelled) setCovered(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lgaName, councilSlug]);

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

  const allControls = categories!.flatMap((cat) => cat.controls);

  return (
    <div className="rounded-xl border border-gray-200 p-4">
      <p className="text-sm font-semibold text-gray-900">
        {lgaName} council&apos;s rules for building here
      </p>
      {/* "these apply to any residential building on this block" was not true
          of a row carrying a condition — many apply only to a bedroom count, a
          lot width or a named locality. The conditions are now shown per row,
          so this says where the numbers come from and leaves what they apply
          to on the row itself. */}
      <p className="text-xs text-gray-500 mt-0.5 mb-2">
        {general
          ? `From the council's own planning rulebook. Where a number applies only in certain cases, the case is shown beneath it.`
          : `From the council's own planning rulebook — the numbers for dual occupancies.`}
      </p>
      <div className="space-y-1">
        {allControls.slice(0, SNAPSHOT_LIMIT).map((c, i) => {
          const v = controlValue(c);
          return (
            // Index in the key: control_type + section_ref is NOT unique. A
            // council with per-bedroom parking rates has several rows sharing
            // both, so the old key collided and React rendered one of them.
            <div
              key={`${c.control_type}-${c.section_ref}-${i}`}
              className="flex items-baseline justify-between gap-3 text-sm"
            >
              <span className="text-gray-700 min-w-0">
                {c.control_label}
                {/* The condition is what makes several values for one control
                    readable instead of contradictory. */}
                {c.condition ? (
                  <span className="block text-xs text-gray-500">{c.condition}</span>
                ) : null}
              </span>
              <span className="text-gray-900 font-medium tabular-nums whitespace-nowrap">
                {v}
              </span>
            </div>
          );
        })}
      </div>
      {/* Never truncate silently. Six of nineteen rows looks exactly like all
          nineteen, and a reader who cannot see that more exist has no reason to
          go looking for the one that applies to them. */}
      {allControls.length > SNAPSHOT_LIMIT ? (
        <p className="text-xs text-gray-500 mt-2">
          Showing {SNAPSHOT_LIMIT} of {allControls.length} controls for this council.
        </p>
      ) : null}
    </div>
  );
}

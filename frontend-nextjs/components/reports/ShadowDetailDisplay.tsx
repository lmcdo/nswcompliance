// prior-art-checked: this IS the existing brief ShadowDisplay moved out of
// app/reports/intelligence-brief/page.tsx (which is over 3,000 lines) so the
// scenario table can be render-tested; no second shadow card is being created —
// page.tsx now imports this component in the same render slot.
import { cn } from '@/lib/utils';
import {
  SCENARIO_NOT_ASSESSED_LABEL, isScenarioUnavailable, scenarioUnavailableMessage,
} from '@/lib/not-assessed';

export interface ShadowScenarioRow {
  date_label?: string;
  time_label?: string;
  shadow_length_m?: number | null;
  overlap_pct?: number | null;
  overlaps_subject_lot?: boolean | null;
  // Carried from the service so a scenario with no result can say so. Without
  // these, every measurement is simply null and the row renders as three em
  // dashes — which a reader skims as "nothing to worry about".
  status?: string | null;
  error_note?: string | null;
}

export interface ShadowData {
  height_m?: number | null;
  height_source?: string | null;
  adg_compliant?: boolean | null;
  scenarios?: ShadowScenarioRow[];
  worst_case_scenario?: string | null;
  temporal_caveat?: string | null;
  confidence?: string | null;
}

// Clean a worst-case scenario label for display. The backend labels already
// embed "ADG worst case" and often both a 12-hour and 24-hour time (e.g.
// "ADG worst case 9am Jun 21 09:00"); the UI already prefixes "Worst case (…)",
// so strip the duplicated prefix and the redundant 24-hour time.
export function cleanScenarioLabel(date?: string, time?: string): string {
  let s = [date, time].filter(Boolean).join(' ').trim();
  s = s.replace(/^(adg\s+)?worst\s+case\s+/i, '');
  // If a 12-hour time (9am) is present, drop a redundant HH:MM 24-hour token.
  if (/\b\d{1,2}\s*(am|pm)\b/i.test(s)) {
    s = s.replace(/\s*\b\d{1,2}:\d{2}\b/g, '');
  }
  return s.replace(/\s{2,}/g, ' ').trim();
}

// The shadow field is a nested object — render the overshadowing summary
// (height, solar-access reading, worst-case shadow) plus the full scenario
// table, not a bare "6 fields".
export function ShadowDisplay({ data }: { data: ShadowData }) {
  const scenarios = data.scenarios || [];
  const worst = scenarios.find((s) => `${s.date_label} ${s.time_label}`.trim() === (data.worst_case_scenario || '').trim())
    || scenarios[0];
  const defaultHeight = data.height_source === 'default';
  const lowConfidence = defaultHeight || data.confidence === 'low';
  return (
    <div className="text-sm text-slate-900 space-y-1.5">
      {data.height_m != null && (
        <div>
          Building height used: <span className="font-medium">{data.height_m} m</span>
          <span className="text-slate-500">
            {defaultHeight
              // The 9 m fallback (shadow_detector DEFAULT_HEIGHT_M) — say WHY it
              // was used, not the internal slug.
              ? ' — no LEP height limit is mapped for this lot, so the analysis uses a standard two-storey height'
              : data.height_source
                ? ' — the LEP height limit mapped for this lot'
                : ''}
          </span>
        </div>
      )}
      {data.adg_compliant != null && (
        <div>
          ADG solar access:{' '}
          <span className={cn('inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ring-1',
            data.adg_compliant ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-amber-50 text-amber-700 ring-amber-200')}>
            {data.adg_compliant ? 'meets the 3-hour guideline' : 'below the 3-hour guideline'}
          </span>
          {lowConfidence && (
            <span className="text-slate-500"> — computed at the standard two-storey height — confidence low</span>
          )}
        </div>
      )}
      {data.confidence && (
        <div className="text-slate-500">
          Run confidence: <span className="font-medium text-slate-700">{data.confidence}</span>
        </div>
      )}
      {worst && (worst.shadow_length_m != null || worst.overlap_pct != null) && (
        <div className="text-slate-700">
          Worst case ({cleanScenarioLabel(worst.date_label, worst.time_label)}):{' '}
          {worst.shadow_length_m != null ? `${worst.shadow_length_m} m shadow` : ''}
          {worst.shadow_length_m != null && worst.overlap_pct != null ? ', ' : ''}
          {worst.overlap_pct != null ? `${worst.overlap_pct}% overlap on neighbours` : ''}
        </div>
      )}
      {scenarios.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm mt-1" data-testid="shadow-scenario-table">
            <thead>
              <tr className="text-left text-[11px] font-medium uppercase tracking-wide text-slate-400">
                <th className="py-1 pr-3 font-medium">Scenario</th>
                <th className="py-1 pr-3 font-medium">Time</th>
                <th className="py-1 pr-3 font-medium">Shadow length</th>
                <th className="py-1 pr-3 font-medium">Overlap on neighbours</th>
                <th className="py-1 font-medium">Overlaps this lot</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s, i) => (
                isScenarioUnavailable(s) ? (
                  // One amber statement across the measurement columns, not
                  // three em dashes. An empty cell reads as "fine" to someone
                  // skimming; this has to read as an absence and look unlike a
                  // result.
                  <tr key={i} className="border-t border-slate-100 align-top bg-amber-50">
                    <td className="py-1 pr-3 text-slate-700">{cleanScenarioLabel(s.date_label) || s.date_label || '—'}</td>
                    <td className="py-1 pr-3 tabular-nums text-slate-500">{s.time_label || '—'}</td>
                    <td className="py-1 text-amber-900 text-xs leading-snug" colSpan={3}>
                      <span className="font-medium">{SCENARIO_NOT_ASSESSED_LABEL}</span>
                      {' — '}
                      {scenarioUnavailableMessage(s.error_note)}
                    </td>
                  </tr>
                ) : (
                  <tr key={i} className="border-t border-slate-100 align-top">
                    <td className="py-1 pr-3 text-slate-700">{cleanScenarioLabel(s.date_label) || s.date_label || '—'}</td>
                    <td className="py-1 pr-3 tabular-nums text-slate-500">{s.time_label || '—'}</td>
                    <td className="py-1 pr-3 tabular-nums text-slate-700">{s.shadow_length_m != null ? `${s.shadow_length_m} m` : '—'}</td>
                    <td className="py-1 pr-3 tabular-nums text-slate-700">
                      {s.overlap_pct != null
                        ? `${s.overlap_pct.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`
                        : '—'}
                    </td>
                    <td className="py-1 text-slate-500">
                      {s.overlaps_subject_lot == null ? '—' : s.overlaps_subject_lot ? 'Yes' : 'No'}
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data.temporal_caveat && <div className="text-[11px] text-slate-400 leading-snug mt-1">{data.temporal_caveat}</div>}
    </div>
  );
}

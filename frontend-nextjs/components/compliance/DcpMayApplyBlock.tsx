'use client';

/**
 * Lists areas of a council's plan whose rules may apply to this property: the property is in the
 * area's suburb, but we cannot tell whether it is inside the area. One collapsed amber section
 * per area; the rules are shown so the reader can check them, not as confirmed for this address.
 * Each area links to the plan's own page for it and lets the reader say whether the property is in
 * it; that answer is the reader's own, kept in this browser per address and area.
 *
 * prior-art-checked: extends the council-wide not-covered notice (DcpNotCoveredNotice.tsx) with a
 * per-suburb block; that notice withholds rules, this one shows them with their uncertainty.
 */
import { useEffect, useState } from 'react';
import { pageLabel } from '@/lib/page-citation';
import type { Provision } from '@/components/compliance/PageGroupedProvisions';

export interface MayApplyArea {
  area_id: string;
  /** The chapter the area's rules sit in; lets the council-wide notice drop a chapter shown here. */
  chapter_key?: string;
  title: string;
  reason_code: string;
  reason_text: string;
  applies_to_quote?: string | null;
  applies_to_page?: number | string | null;
  /** Cropped picture of the plan's map for this area; absent until the images are uploaded. */
  map_image_url?: string | null;
  /** The PDF page the map image was cut from (may differ from applies_to_page). */
  map_page?: number | null;
  suburb: string;
  provisions?: Provision[] | null;
}

const COLLAPSE_AFTER = 3;

export type MayApplyAnswer = 'in' | 'out' | 'unsure';

/** The plan's own page for an area. Only a .pdf address can take a #page anchor (never over an existing '#'). */
export function areaPlanLink(
  url: string | undefined | null,
  page: number | string | null | undefined,
): { href: string; page: number | null } | null {
  if (!url) return null;
  const n = typeof page === 'string' ? Number(page) : page;
  const isPdf = /\.pdf(\?|#|$)/i.test(url);
  if (isPdf && typeof n === 'number' && Number.isInteger(n) && n > 0 && !url.includes('#')) {
    return { href: `${url}#page=${n}`, page: n };
  }
  return { href: url, page: null };
}

const storeKey = (address: string, areaId: string) => `dcp-may-apply:v1:${address}:${areaId}`;

function readAnswer(address: string, areaId: string): MayApplyAnswer {
  try {
    const v = window.localStorage.getItem(storeKey(address, areaId));
    return v === 'in' || v === 'out' ? v : 'unsure';
  } catch {
    return 'unsure';
  }
}

function writeAnswer(address: string, areaId: string, a: MayApplyAnswer): void {
  try {
    if (a === 'unsure') window.localStorage.removeItem(storeKey(address, areaId));
    else window.localStorage.setItem(storeKey(address, areaId), a);
  } catch {
    /* storage unavailable: the answer lasts for this visit only */
  }
}

const AMBER = 'text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5';

const CHOICES = [
  ['in', 'My property is in this area'],
  ['out', 'My property is not in this area'],
  ['unsure', 'Not sure'],
] as const;

export function DcpMayApplyBlock({
  mayApply,
  address,
  chapterPdfUrls,
}: {
  mayApply: MayApplyArea[] | null | undefined;
  address?: string;
  chapterPdfUrls?: Record<string, string> | null;
}) {
  const [answers, setAnswers] = useState<Record<string, MayApplyAnswer>>({});
  const addr = address ?? '';
  const ids = (mayApply ?? []).map((a) => a.area_id).join('|');

  useEffect(() => {
    if (!addr) return;
    const next: Record<string, MayApplyAnswer> = {};
    for (const id of ids ? ids.split('|') : []) next[id] = readAnswer(addr, id);
    setAnswers(next);
  }, [addr, ids]);

  if (!mayApply || mayApply.length === 0) return null;

  const answer = (id: string, a: MayApplyAnswer) => {
    setAnswers((prev) => ({ ...prev, [id]: a }));
    if (addr) writeAnswer(addr, id, a);
  };

  const list = (
    <div className="space-y-2">
      {mayApply.map((area) => {
        const ans = answers[area.area_id] ?? 'unsure';
        if (ans === 'out') {
          return (
            <p key={area.area_id} data-testid="dcp-may-apply-area-out" className={AMBER}>
              {area.title}: You said your property is not in this area.{' '}
              <button type="button" onClick={() => answer(area.area_id, 'unsure')} className="underline text-sky-800">
                Change
              </button>
            </p>
          );
        }
        // A missing list is a loading failure, not "0 rules": say so (Sol, 2026-10-20).
        const loaded = Array.isArray(area.provisions);
        const rules: Provision[] = loaded ? (area.provisions as Provision[]) : [];
        // The map link opens the page the map is drawn on when we know it, else where the land is described.
        const link = areaPlanLink(area.chapter_key ? chapterPdfUrls?.[area.chapter_key] : undefined, area.map_page ?? area.applies_to_page);
        const count = loaded ? ` (${rules.length} ${rules.length === 1 ? 'rule' : 'rules'})` : '';
        return (
          <details
            key={`${area.area_id}:${ans}`}
            data-testid="dcp-may-apply-area"
            open={ans === 'in' ? true : undefined}
            className={AMBER}
          >
            <summary className="cursor-pointer">
              {ans === 'in'
                ? `${area.title}: You said your property is in this area — these rules apply to it${count}`
                : `Rules for ${area.title} may apply to this property${count}`}
            </summary>
            <p className="mt-2">
              This property is in {area.suburb}. We can’t tell whether it is inside this area. {area.reason_text}
              {area.applies_to_quote ? (
                <>
                  {' '}The plan says: “{area.applies_to_quote}”
                  {area.applies_to_page != null ? ` (page ${area.applies_to_page})` : ''}.
                </>
              ) : null}{' '}
              These rules are shown so you can check them; we have not been able to check that they cover this address.
            </p>
            {link && (
              <p className="mt-2">
                <a
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="dcp-may-apply-map-link"
                  className="underline text-sky-800"
                >
                  See the plan’s map of this area{link.page !== null ? ` (page ${link.page})` : ''}
                </a>
                {area.map_image_url && (
                  <a href={link.href} target="_blank" rel="noopener noreferrer" className="mt-2 block">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={area.map_image_url}
                      loading="lazy"
                      alt={`The plan’s map of ${area.title}${link.page !== null ? `, page ${link.page}` : ''}`}
                      data-testid="dcp-may-apply-map-thumb"
                      className="max-w-[320px] w-full h-auto border border-amber-200 rounded"
                    />
                  </a>
                )}
              </p>
            )}
            <div className="mt-2" role="group" aria-label={`Is your property in ${area.title}?`}>
              {CHOICES.map(([v, label]) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={ans === v}
                  onClick={() => answer(area.area_id, v)}
                  className={`mr-2 mb-1 rounded border px-2 py-0.5 ${ans === v ? 'bg-amber-200 border-amber-400 font-medium' : 'bg-white border-amber-200'}`}
                >
                  {label}
                </button>
              ))}
            </div>
            {!loaded && (
              <p className="mt-2 font-medium">We couldn’t load the rules for this area. Please try again later.</p>
            )}
            <ul className="mt-2 space-y-2">
              {rules.map((p) => {
                const page = pageLabel(p);
                return (
                  <li key={p.id} data-testid="dcp-may-apply-rule" className="bg-white border border-amber-200 rounded p-2 text-gray-800">
                    <p className="whitespace-pre-line">{p.provision_text}</p>
                    {page && <p className="mt-1 text-gray-500">{page}</p>}
                  </li>
                );
              })}
            </ul>
          </details>
        );
      })}
    </div>
  );

  if (mayApply.length > COLLAPSE_AFTER) {
    return (
      <details data-testid="dcp-may-apply-block" className="mb-3">
        <summary className={`cursor-pointer ${AMBER}`}>
          Rules for areas that may apply to this property ({mayApply.length})
        </summary>
        <div className="mt-2">{list}</div>
      </details>
    );
  }
  return (
    <div data-testid="dcp-may-apply-block" className="mb-3">
      {list}
    </div>
  );
}

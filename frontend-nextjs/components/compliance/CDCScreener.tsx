'use client';

/**
 * CDCScreener - Complying Development Certificate preliminary screener
 *
 * Pure TypeScript logic against SEPP E&C provisions already loaded in
 * ExemptComplyingProvisions. Gives a quick pass/fail verdict with per-criterion
 * breakdown so certifiers can immediately identify blocking constraints.
 */

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface CDCCriterion {
  label: string;
  result: 'pass' | 'fail' | 'warn' | 'unknown';
  detail: string;
  provisionRef?: string;
}

interface CDCScreenerProps {
  zoneCode: string;
  lotArea?: number | null;        // m² — pre-filled from property context
  heritageItem?: boolean;         // pre-filled from property context
  provisions: Array<{
    provision_text: string;
    v2_topic?: string;
    v2_part?: string;
  }>;
}

interface ProposedValues {
  floorAreaAddition: string;   // m²
  proposedHeight: string;      // m
  frontSetback: string;        // m
  sideSetback: string;         // m
}

/** Extract the first numeric value matching a given unit from text */
function extractNumeric(text: string, unit: 'm' | 'm²' | '%'): number | null {
  const patterns: Record<string, RegExp> = {
    'm': /\b(\d+(?:\.\d+)?)\s*(?:m|metres?|meters?)\b/i,
    'm²': /\b(\d+(?:\.\d+)?)\s*(?:m²|m2|sqm|square metres?)\b/i,
    '%': /\b(\d+(?:\.\d+)?)\s*%/i,
  };
  const match = text.match(patterns[unit]);
  return match ? parseFloat(match[1]) : null;
}

/**
 * Evaluate CDC criteria using zone, lot area, heritage flag and provision texts.
 * Returns list of criteria with pass/fail/warn results.
 */
function evaluateCriteria(
  zoneCode: string,
  lotArea: number | null,
  heritageItem: boolean,
  proposed: ProposedValues,
  provisions: CDCScreenerProps['provisions']
): CDCCriterion[] {
  const criteria: CDCCriterion[] = [];
  const floorAddition = parseFloat(proposed.floorAreaAddition) || 0;
  const height = parseFloat(proposed.proposedHeight) || 0;

  // ── 1. Heritage Item ─────────────────────────────────────────────────────
  criteria.push({
    label: 'Not a heritage item',
    result: heritageItem ? 'fail' : 'pass',
    detail: heritageItem
      ? 'Properties listed as heritage items are not eligible for CDC. A DA is required.'
      : 'Property is not listed as a heritage item.',
    provisionRef: 'SEPP E&C — General exclusion',
  });

  // ── 2. Residential zone ──────────────────────────────────────────────────
  const residentialZones = ['R1', 'R2', 'R3', 'R4', 'RU5'];
  const isResidential = residentialZones.includes(zoneCode);
  criteria.push({
    label: 'Residential zone',
    result: isResidential ? 'pass' : 'warn',
    detail: isResidential
      ? `${zoneCode} is a residential zone — Housing Code applies.`
      : `${zoneCode} may not be covered by the Housing Code. Verify Part eligibility.`,
    provisionRef: 'SEPP E&C Part 3',
  });

  // ── 3. Lot area ──────────────────────────────────────────────────────────
  if (lotArea) {
    // Find min lot area from loaded provisions
    const lotProvision = provisions.find(p =>
      /minimum lot area|lot size/i.test(p.provision_text)
    );
    const minLot = lotProvision ? extractNumeric(lotProvision.provision_text, 'm²') : 450;
    const limit = minLot || 450;
    criteria.push({
      label: `Minimum lot area (${limit} m²)`,
      result: lotArea >= limit ? 'pass' : 'fail',
      detail: `Lot is ${Math.round(lotArea)} m² — ${lotArea >= limit ? 'meets' : 'does not meet'} the ${limit} m² minimum.`,
      provisionRef: lotProvision ? `Part ${lotProvision.v2_part}` : 'SEPP E&C Cl 3.1',
    });
  } else {
    criteria.push({
      label: 'Minimum lot area',
      result: 'unknown',
      detail: 'Lot area not available — enter below to check.',
    });
  }

  // ── 4. Floor area addition ───────────────────────────────────────────────
  if (floorAddition > 0) {
    // Scan provisions for maximum floor area or GFA limit
    const gfaProvision = provisions.find(p =>
      /floor area|gross floor area|GFA/i.test(p.provision_text) &&
      /maximum|must not exceed/i.test(p.provision_text)
    );
    const maxGfa = gfaProvision ? extractNumeric(gfaProvision.provision_text, 'm²') : null;

    if (maxGfa) {
      criteria.push({
        label: `Maximum floor area addition (${maxGfa} m²)`,
        result: floorAddition <= maxGfa ? 'pass' : 'fail',
        detail: `${floorAddition} m² proposed — ${floorAddition <= maxGfa ? 'within' : 'exceeds'} the ${maxGfa} m² limit.`,
        provisionRef: gfaProvision ? `Part ${gfaProvision.v2_part}` : undefined,
      });
    } else {
      criteria.push({
        label: 'Floor area addition',
        result: 'unknown',
        detail: `${floorAddition} m² proposed. Verify against applicable standard in Part ${zoneCode.startsWith('R') ? '3' : '?'}.`,
      });
    }
  }

  // ── 5. Height ────────────────────────────────────────────────────────────
  if (height > 0) {
    const heightProvision = provisions.find(p =>
      /height of building|wall height|maximum height/i.test(p.provision_text) &&
      /maximum|must not exceed/i.test(p.provision_text)
    );
    const maxHeight = heightProvision ? extractNumeric(heightProvision.provision_text, 'm') : 8.5;
    const limit = maxHeight || 8.5;

    criteria.push({
      label: `Maximum height (${limit} m)`,
      result: height <= limit ? 'pass' : 'fail',
      detail: `${height} m proposed — ${height <= limit ? 'within' : 'exceeds'} the ${limit} m maximum.`,
      provisionRef: heightProvision ? `Part ${heightProvision.v2_part}` : 'SEPP E&C Cl 3.18',
    });
  }

  return criteria;
}

export function CDCScreener({ zoneCode, lotArea, heritageItem = false, provisions }: CDCScreenerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [manualLotArea, setManualLotArea] = useState('');
  const [proposed, setProposed] = useState<ProposedValues>({
    floorAreaAddition: '',
    proposedHeight: '',
    frontSetback: '',
    sideSetback: '',
  });

  const effectiveLotArea = lotArea || (manualLotArea ? parseFloat(manualLotArea) : null);

  const criteria = evaluateCriteria(zoneCode, effectiveLotArea, heritageItem, proposed, provisions);

  const failCount = criteria.filter(c => c.result === 'fail').length;
  const warnCount = criteria.filter(c => c.result === 'warn').length;
  const passCount = criteria.filter(c => c.result === 'pass').length;
  const isEligible = failCount === 0 && criteria.every(c => c.result !== 'unknown');
  const hasUnknowns = criteria.some(c => c.result === 'unknown');

  const verdictColor = failCount > 0
    ? 'bg-red-50 border-red-300'
    : warnCount > 0 || hasUnknowns
    ? 'bg-amber-50 border-amber-300'
    : 'bg-green-50 border-green-300';

  const verdictText = failCount > 0
    ? `Not CDC Eligible (${failCount} criterion${failCount > 1 ? 'a' : 'ion'} failed)`
    : hasUnknowns
    ? 'Incomplete — enter values below to check'
    : warnCount > 0
    ? 'Likely Eligible — verify flagged items'
    : 'Likely CDC Eligible';

  const VerdictIcon = failCount > 0 ? XCircle : hasUnknowns || warnCount > 0 ? AlertCircle : CheckCircle;
  const verdictIconColor = failCount > 0 ? 'text-red-600' : warnCount > 0 || hasUnknowns ? 'text-amber-600' : 'text-green-600';

  return (
    <div className="mb-4 border border-purple-200 rounded-lg overflow-hidden">
      {/* Screener header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-purple-50 hover:bg-purple-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <VerdictIcon className={`w-4 h-4 ${verdictIconColor}`} />
          <span className="text-sm font-medium text-purple-900">CDC Eligibility Screener</span>
          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
            failCount > 0 ? 'bg-red-100 text-red-800 border-red-300' :
            hasUnknowns ? 'bg-gray-100 text-gray-600 border-gray-300' :
            warnCount > 0 ? 'bg-amber-100 text-amber-800 border-amber-300' :
            'bg-green-100 text-green-800 border-green-300'
          }`}>
            {verdictText}
          </span>
        </div>
        <span className="text-purple-600 text-xs">{isOpen ? '▲ Hide' : '▼ Show'}</span>
      </button>

      {isOpen && (
        <div className="px-4 py-3 bg-white space-y-3">
          {/* Proposed values inputs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {!lotArea && (
              <div>
                <label className="block text-xs text-gray-600 mb-1">Lot area (m²)</label>
                <input
                  type="number" min="0" step="1"
                  value={manualLotArea}
                  onChange={e => setManualLotArea(e.target.value)}
                  placeholder="e.g. 600"
                  className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-purple-400"
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-gray-600 mb-1">Floor area addition (m²)</label>
              <input
                type="number" min="0" step="1"
                value={proposed.floorAreaAddition}
                onChange={e => setProposed(p => ({ ...p, floorAreaAddition: e.target.value }))}
                placeholder="0"
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-purple-400"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Proposed height (m)</label>
              <input
                type="number" min="0" step="0.1"
                value={proposed.proposedHeight}
                onChange={e => setProposed(p => ({ ...p, proposedHeight: e.target.value }))}
                placeholder="0.0"
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-purple-400"
              />
            </div>
          </div>

          {/* Criteria list */}
          <div className="space-y-1.5">
            {criteria.map((c, idx) => (
              <div key={idx} className={`flex items-start gap-2 px-3 py-2 rounded border text-xs ${
                c.result === 'pass' ? 'bg-green-50 border-green-200' :
                c.result === 'fail' ? 'bg-red-50 border-red-200' :
                c.result === 'warn' ? 'bg-amber-50 border-amber-200' :
                'bg-gray-50 border-gray-200'
              }`}>
                {c.result === 'pass' && <CheckCircle className="w-3.5 h-3.5 text-green-600 shrink-0 mt-0.5" />}
                {c.result === 'fail' && <XCircle className="w-3.5 h-3.5 text-red-600 shrink-0 mt-0.5" />}
                {c.result === 'warn' && <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />}
                {c.result === 'unknown' && <AlertCircle className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-0.5" />}
                <div className="flex-1">
                  <span className={`font-medium ${c.result === 'fail' ? 'text-red-800' : c.result === 'warn' ? 'text-amber-800' : c.result === 'pass' ? 'text-green-800' : 'text-gray-600'}`}>
                    {c.label}
                  </span>
                  <span className="text-gray-600 ml-1">— {c.detail}</span>
                  {c.provisionRef && (
                    <span className="ml-1 text-gray-400">({c.provisionRef})</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className="text-xs text-gray-400">
            Preliminary screener only — verify against current SEPP (Exempt and Complying Development Codes) 2008 before issuing CDC.
          </p>
        </div>
      )}
    </div>
  );
}

'use client';

/**
 * ExemptComplyingProvisions
 *
 * Certifier-facing browser for SEPP Exempt and Complying Development Codes 2008.
 * Shows actionable standards for a given work type, filtered to the applicable
 * housing code Part based on the property's zone.
 *
 * Zone → Part mapping:
 *   R1, R2, R3, R4, RU5 → Part 3 (Housing Code)
 *   R5, RU1–RU6          → Part 3A (Rural Housing Code)
 */

import { useState, useEffect } from 'react';
import { CDC_HOUSING_CODE_ZONES } from '@/lib/regulatory-constants';
import { ChevronDown, ChevronRight, ChevronUp, ExternalLink, FileText, FileImage, Clock, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getPdfImageUrl } from '@/lib/pdf-image-url';
import { sanitizeHTML } from '@/lib/sanitize';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { CDCScreener } from './CDCScreener';

const WORK_TYPES = [
  { key: 'Deck',    label: 'Deck / Balcony' },
  { key: 'Fence',   label: 'Fence' },
  { key: 'Carport', label: 'Carport' },
  { key: 'Pool',    label: 'Pool' },
] as const;

type WorkTypeKey = typeof WORK_TYPES[number]['key'];

const PART_NAMES: Record<string, string> = {
  '3':  'Part 3 — Housing Code',
  '3A': 'Part 3A — Rural Housing Code',
  '3B': 'Part 3B — Low Rise Housing Diversity Code',
  '3C': 'Part 3C — Greenfield Housing Code',
  '3D': 'Part 3D — Inland Code',
};

interface Provision {
  id: number;
  pdf_page: number | null;
  pdf_printed_page: number | null;
  provision_text: string;
  v2_part: string;
  v2_topic: string;
}

interface Props {
  zoneCode: string;           // e.g. "R2"
  lotArea?: number | null;    // m² — from property context
  heritageItem?: boolean;     // true = individually listed heritage item (LEP Schedule 5)
  heritageAffected?: boolean; // true = any heritage flag (item OR conservation area)
  isStrata?: boolean;         // true = strata unit — lot area figures are parent lot, not unit
}

export function ExemptComplyingProvisions({ zoneCode, lotArea, heritageItem = false, heritageAffected = false, isStrata = false }: Props) {
  const residentialZones = CDC_HOUSING_CODE_ZONES;
  const [expanded, setExpanded] = useState(residentialZones.includes(zoneCode));
  const [selectedType, setSelectedType] = useState<WorkTypeKey | null>(null);
  const [provisions, setProvisions] = useState<Provision[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [part, setPart] = useState('');
  const [loading, setLoading] = useState(false);
  const [viewingPdfPage, setViewingPdfPage] = useState<{pageNumber: number, url: string, label: string} | null>(null);

  // Fetch counts on mount
  useEffect(() => {
    if (!zoneCode) return;
    fetch(`/api/sepp/exempt-complying?zone=${zoneCode}`)
      .then(r => r.json())
      .then(data => {
        setCounts(data.counts || {});
        setPart(data.part || '');
      })
      .catch(() => {});
  }, [zoneCode]);

  // Fetch provisions when work type selected
  useEffect(() => {
    if (!selectedType || !zoneCode) return;
    setLoading(true);
    fetch(`/api/sepp/exempt-complying?zone=${zoneCode}&workType=${selectedType}`)
      .then(r => r.json())
      .then(data => {
        setProvisions(data.provisions || []);
        setPart(data.part || '');
      })
      .catch(() => setProvisions([]))
      .finally(() => setLoading(false));
  }, [selectedType, zoneCode]);

  const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
  if (totalCount === 0 && !loading) return null;

  const partName = PART_NAMES[part] || `Part ${part}`;

  return (
    <Card className="border-purple-200 bg-purple-50/30">
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {expanded
              ? <ChevronDown className="h-5 w-5 text-purple-600" />
              : <ChevronRight className="h-5 w-5 text-purple-600" />
            }
            <FileText className="h-5 w-5 text-purple-700" />
            <CardTitle className="text-lg text-purple-900">
              Exempt &amp; Complying Development Standards
            </CardTitle>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <Badge className="bg-purple-100 text-purple-800 text-xs pointer-events-none">
            {partName}
          </Badge>
          <span className="text-xs text-purple-600">
            Applies to {zoneCode} zone
          </span>
          <Badge variant="outline" className="text-xs text-gray-500 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Updated Feb 2026
          </Badge>
          {!expanded && totalCount > 0 && (
            <span className="text-xs text-purple-600">
              · {totalCount} actionable standards across {Object.keys(counts).length} work types
            </span>
          )}
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          {isStrata && (
            <div className="mb-3 bg-orange-50 border border-orange-200 rounded px-3 py-2 flex items-start gap-2 text-xs">
              <Shield className="h-3.5 w-3.5 text-orange-500 flex-shrink-0 mt-0.5" />
              <span className="text-orange-800">
                <span className="font-semibold">Strata unit — </span>
                Lot area figures below apply to the parent lot. For individual unit works (decks, fences within a lot), confirm area with your strata plan. Works affecting common property require owners corporation consent.
              </span>
            </div>
          )}
          <p className="text-sm text-purple-700 mb-4">
            Standards that apply to development that may proceed as complying development
            on this property. Click a work type to view the applicable standards.
          </p>

          {/* CDC Eligibility Screener */}
          <CDCScreener
            zoneCode={zoneCode}
            lotArea={lotArea}
            heritageItem={heritageItem}
            heritageAffected={heritageAffected}
            provisions={provisions}
          />

          {/* Work type tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {WORK_TYPES.map(({ key, label }) => {
              const count = counts[key] || 0;
              const active = selectedType === key;
              return (
                <button
                  key={key}
                  onClick={() => setSelectedType(active ? null : key)}
                  className={[
                    'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors flex items-center gap-1',
                    active
                      ? 'bg-purple-700 text-white border-purple-700'
                      : count > 0
                        ? 'bg-white text-purple-800 border-purple-300 hover:bg-purple-50'
                        : 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed',
                  ].join(' ')}
                  disabled={count === 0}
                >
                  {active && <ChevronUp className="h-4 w-4" />}
                  <span>{label}</span>
                  {count > 0 && (
                    <span className={`ml-1.5 text-xs ${active ? 'text-purple-200' : 'text-purple-500'}`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Provisions list */}
          {loading && (
            <div className="text-sm text-purple-600 py-4">Loading provisions…</div>
          )}

          {!loading && selectedType && provisions.length === 0 && (
            <div className="text-sm text-gray-500 py-4">No actionable standards found for this work type and zone.</div>
          )}

          {!loading && selectedType && provisions.length > 0 && (
            <div className="space-y-2">
              {provisions.map(p => {
                const page = p.pdf_printed_page || p.pdf_page;

                // Extract sub-clause from provision text (e.g., "(a)", "(1)", "(2)(b)")
                const subClauseMatch = p.provision_text.match(/^\(([^)]+)\)/);
                const displayNumber = subClauseMatch
                  ? `Part ${p.v2_part} ${subClauseMatch[0]}`
                  : `Part ${p.v2_part}`;

                return (
                  <div
                    key={p.id}
                    className="bg-white rounded border border-purple-100 px-3 py-2.5"
                  >
                    {/* Provision number badge */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-medium text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                        {displayNumber}
                      </span>
                      <span className="text-xs text-gray-400">
                        {p.v2_topic}
                      </span>
                    </div>

                    {/* Provision text + PDF button */}
                    <div className="flex items-start justify-between gap-2">
                      <div
                        className="text-sm text-gray-800 leading-relaxed flex-1 [&_table]:w-full [&_table]:border-collapse [&_table]:my-1 [&_td]:border [&_td]:border-gray-200 [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs"
                        dangerouslySetInnerHTML={{ __html: sanitizeHTML(p.provision_text) }}
                      />
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {page && (
                          <>
                            <button
                              onClick={() => setViewingPdfPage({
                                pageNumber: page,
                                url: getPdfImageUrl(`/pdf-pages/sepp-exempt-complying/page_${page}.png`) || '',
                                label: `SEPP E&C Part ${p.v2_part} - Page ${page}`
                              })}
                              className="p-1 rounded hover:bg-purple-100 transition-colors"
                              title="View PDF page"
                            >
                              <FileImage className="w-4 h-4 text-purple-600 hover:text-purple-800" />
                            </button>
                            <span className="text-xs text-gray-400 whitespace-nowrap">
                              p.{page}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Footer */}
          <div className="mt-4 pt-3 border-t border-purple-100 space-y-3">
            {/* Next Steps Checklist */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-xs font-medium text-blue-900 mb-2">
                ✓ How to Use Complying Development
              </p>
              <div className="text-xs text-blue-800 space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 font-mono mt-0.5">☐</span>
                  <span>Review all {partName} standards above for your work type</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 font-mono mt-0.5">☐</span>
                  <span>Check <strong>LEP tab</strong> confirms your use is permitted in this zone</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 font-mono mt-0.5">☐</span>
                  <span>Review <strong>DCP tab</strong> for additional local height/setback rules</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 font-mono mt-0.5">☐</span>
                  <span>Engage a private certifier to lodge CDC application</span>
                </div>
              </div>
              <p className="text-xs text-blue-700 mt-2">
                All three requirements (SEPP + LEP + DCP) must be satisfied for Complying Development.
              </p>
            </div>

            {/* Legal reference */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-xs text-gray-500">
                Showing {partName} standards only. Other codes may apply — see all provisions for confirmation.
              </p>
              <a
                href="https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-572"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-purple-700 hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                View full SEPP on NSW Legislation
              </a>
            </div>

            {/* Compliance-grade guarantee */}
            <div className="flex items-center gap-2 text-xs text-gray-600 border-t border-purple-100 pt-3">
              <Shield className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span>Provision text extracted from SEPP (Exempt and Complying Development Codes) 2008. Zone eligibility and property-specific constraints must be independently verified before issuing a CDC.</span>
            </div>
          </div>
        </CardContent>
      )}

      {/* PDF Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfPage}
        onClose={() => setViewingPdfPage(null)}
        imageUrl={viewingPdfPage?.url || null}
        pageNumber={viewingPdfPage?.pageNumber}
        title={viewingPdfPage?.label}
      />
    </Card>
  );
}

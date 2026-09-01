'use client';

/**
 * DcpStructuredControls — displays extracted numeric DCP controls
 * from dcp_setback_controls table as a summary card.
 *
 * Shows deterministic, structured values (setbacks, parking rates,
 * landscaping %, site coverage) with formal DCP citations.
 */

import React, { useState } from 'react';
import useSWR from 'swr';
import { ChevronDown, ChevronRight, Ruler, Car, TreePine, Building2, Maximize2, LayoutGrid, FileText, ExternalLink, Sun, Eye, Home, AlertCircle, MinusCircle } from 'lucide-react';

type ControlDataStatus = 'numeric' | 'not_applicable' | 'under_review';
type ControlDirection = 'min' | 'max';

interface StructuredControl {
  control_type: string;
  control_label: string;
  // 'max' → the value is a ceiling (render "≤"); 'min'/absent → a floor ("≥").
  direction?: ControlDirection;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  condition: string | null;
  section_ref: string | null;
  source_text: string | null;
  dcp_name: string | null;
  dcp_version: string | null;
  pdf_page: number | null;
  pdf_url: string | null;
  data_status?: ControlDataStatus;
}

interface ControlCategory {
  category: string;
  order: number;
  controls: StructuredControl[];
}

interface StructuredControlsResponse {
  council: string;
  dev_type: string;
  has_controls: boolean;
  dcp_name: string | null;
  /** Dev types this council DOES have controls for. The only field that answers
   *  the COUNCIL-level question — has_controls is scoped to the REQUESTED
   *  dev_type alone, so it cannot distinguish "this council has nothing" from
   *  "nothing for this type". Absent is not the same as empty: see the
   *  undefined branch below. */
  available_dev_types?: string[];
  categories: ControlCategory[];
}

interface DcpStructuredControlsProps {
  formerCouncil: string;
  devType?: string;
  /**
   * Rendered INSTEAD of this card when the council has no extracted controls.
   *
   * The caller cannot decide this for itself: has_controls is only known after
   * this component's own fetch resolves. Before this existed the caller rendered
   * a "DCP not yet processed" form alongside the controls, so a council with 20
   * extracted controls was told its DCP was not processed - on the same screen
   * that listed them, with the source plan named.
   */
  fallback?: React.ReactNode;
}

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch structured controls');
  return res.json();
};

const CATEGORY_ICONS: Record<string, typeof Ruler> = {
  'Setbacks': Ruler,
  'Parking': Car,
  'Landscaping & Canopy': TreePine,
  'Site Coverage': Maximize2,
  'Height': Building2,
  'Open Space': LayoutGrid,
  'Solar & Amenity': Sun,
  'Privacy': Eye,
  'Fencing': Ruler,
  'Dwelling Size': Home,
};

const CATEGORY_COLORS: Record<string, string> = {
  'Setbacks': 'border-blue-200 bg-blue-50',
  'Parking': 'border-amber-200 bg-amber-50',
  'Landscaping & Canopy': 'border-green-200 bg-green-50',
  'Site Coverage': 'border-purple-200 bg-purple-50',
  'Height': 'border-slate-200 bg-slate-50',
  'Open Space': 'border-teal-200 bg-teal-50',
  'Solar & Amenity': 'border-yellow-200 bg-yellow-50',
  'Privacy': 'border-indigo-200 bg-indigo-50',
  'Fencing': 'border-orange-200 bg-orange-50',
  'Dwelling Size': 'border-rose-200 bg-rose-50',
};

export function formatValue(control: StructuredControl): string {
  const { value_min, value_max, unit, direction } = control;
  const unitStr = unit ? ` ${unit}` : '';

  if (value_min !== null && value_max !== null) {
    if (value_min === value_max) return `${value_min}${unitStr}`;
    return `${value_min}–${value_max}${unitStr}`;
  }
  // A maximum control (e.g. max site coverage, max height) stores its ceiling
  // in value_min. Render it "≤" — rendering "≥" would state the inverse of the
  // control, a wrong regulatory result on a compliance surface.
  if (value_min !== null) {
    return `${direction === 'max' ? '≤' : '≥'} ${value_min}${unitStr}`;
  }
  if (value_max !== null) return `≤ ${value_max}${unitStr}`;
  return '—';
}

function hasNumericValue(control: StructuredControl): boolean {
  return control.value_min !== null || control.value_max !== null;
}

/** Build a formal citation string: "Bayside DCP 2022, s 5.2.1, p 200" */
function formatCitation(control: StructuredControl): string {
  const parts: string[] = [];
  if (control.dcp_name) parts.push(control.dcp_name);
  if (control.section_ref) parts.push(`s ${control.section_ref}`);
  if (control.pdf_page) parts.push(`p ${control.pdf_page}`);
  return parts.join(', ');
}

export function DcpStructuredControls({
  formerCouncil,
  devType = 'dwelling_house',
  fallback = null,
}: DcpStructuredControlsProps) {
  const [expanded, setExpanded] = useState(true);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  const apiUrl = formerCouncil
    ? `/api/dcp/structured-controls?council=${encodeURIComponent(formerCouncil)}&dev_type=${encodeURIComponent(devType)}`
    : null;

  const { data, isLoading } = useSWR<StructuredControlsResponse>(
    apiUrl, fetcher, { revalidateOnFocus: false }
  );

  if (isLoading) {
    return (
      <div className="mb-4 border border-teal-200 rounded-lg p-4 bg-teal-50/50">
        <div className="flex items-center gap-2 text-sm text-teal-700">
          <div className="w-4 h-4 border-2 border-teal-400 border-t-transparent rounded-full animate-spin" />
          Loading structured controls...
        </div>
      </div>
    );
  }

  if (!data?.has_controls) {
    // has_controls is scoped to the REQUESTED dev type. A council with controls
    // for dual_occupancy but none for dwelling_house returns false here, and
    // showing the "not yet processed" fallback would repeat the contradiction
    // this component was just changed to remove - in a narrower case. Only an
    // empty available_dev_types means the council genuinely has nothing.
    // Three states, not two. ABSENT is not EMPTY: an older deployment or a
    // failed query returns {has_controls:false} with no available_dev_types at
    // all, and `?? []` would read that as "this council definitely has nothing"
    // and show the not-processed form. Only an explicitly empty array is
    // evidence of that.
    const otherTypes = data?.available_dev_types;
    if (otherTypes === undefined) {
      return (
        <div className="mb-4 border border-gray-200 rounded-lg p-4 bg-gray-50/60">
          <p className="text-sm text-gray-700">
            No numeric controls returned for this development type.
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Whether this council has controls for other types could not be
            established.
          </p>
        </div>
      );
    }
    if (otherTypes.length > 0) {
      return (
        <div className="mb-4 border border-gray-200 rounded-lg p-4 bg-gray-50/60">
          <p className="text-sm text-gray-700">
            No numeric controls extracted for this development type yet.
          </p>
          <p className="mt-1 text-xs text-gray-500">
            This council has controls for: {otherTypes.join(', ').replace(/_/g, ' ')}.
          </p>
        </div>
      );
    }
    return <>{fallback}</>;
  }

  const totalControls = data.categories.reduce((sum, cat) => sum + cat.controls.length, 0);

  // Shown BELOW the controls. Says what is present and what is not, without
  // offering to notify the reader about a council whose controls they are
  // currently reading - which is what the old interest form did here.
  const textNotLoadedNote = (
    <p className="mt-3 text-xs text-gray-500">
      These are the measurable controls extracted from the published plan. The
      full chapter text for this council is not loaded yet.
    </p>
  );

  return (
    <div className="mb-4 border border-teal-200 rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-teal-50 hover:bg-teal-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-teal-600" />
          <span className="text-sm font-semibold text-teal-900">
            DCP Numeric Controls
          </span>
          <span className="text-xs text-teal-600 bg-teal-100 px-2 py-0.5 rounded-full">
            {totalControls} controls extracted
          </span>
        </div>
        {expanded
          ? <ChevronDown className="w-4 h-4 text-teal-500" />
          : <ChevronRight className="w-4 h-4 text-teal-500" />
        }
      </button>

      {expanded && (
        <div className="p-4 space-y-3">
          {/* DCP source attribution */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <FileText className="w-3 h-3" />
            <span>
              Source: <span className="font-medium text-gray-700">{data.dcp_name || formerCouncil.replace(/_/g, ' ') + ' DCP'}</span>
            </span>
            <span className="text-gray-300">|</span>
            <span>Development type: <span className="font-medium text-gray-700">{devType.replace(/_/g, ' ')}</span></span>
          </div>

          {data.categories.map((category) => {
            const Icon = CATEGORY_ICONS[category.category] || Ruler;
            const colorClass = CATEGORY_COLORS[category.category] || 'border-gray-200 bg-gray-50';

            return (
              <div key={category.category} className={`border rounded-lg overflow-hidden ${colorClass}`}>
                <div className="px-3 py-2 flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5 text-gray-600" />
                  <span className="text-xs font-semibold text-gray-800">{category.category}</span>
                </div>
                <div className="bg-white divide-y divide-gray-100">
                  {category.controls.map((control, i) => {
                    const rowKey = `${control.control_type}-${i}`;
                    const isSourceExpanded = expandedSource === rowKey;
                    const citation = formatCitation(control);

                    const status: ControlDataStatus = control.data_status
                      ?? (hasNumericValue(control) ? 'numeric' : 'not_applicable');

                    return (
                      <div key={rowKey}>
                        <div className="flex items-center px-3 py-2 text-sm">
                          {/* Control name */}
                          <div className="text-gray-700 font-medium w-1/4 flex-shrink-0">
                            {control.control_label}
                          </div>
                          {/* Value — three states */}
                          <div className="text-right w-[100px] flex-shrink-0">
                            {status === 'numeric' ? (
                              <span className="font-mono text-sm font-semibold text-gray-900">
                                {formatValue(control)}
                              </span>
                            ) : status === 'under_review' ? (
                              <span className="inline-flex items-center gap-0.5 text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                                <AlertCircle className="w-3 h-3" />
                                pending
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-0.5 text-xs text-gray-400">
                                <MinusCircle className="w-3 h-3" />
                                assessed on merit
                              </span>
                            )}
                          </div>
                          {/* Condition */}
                          <div className={`text-xs px-3 flex-1 min-w-0 ${
                            status === 'not_applicable' ? 'text-gray-600 italic' : 'text-gray-500'
                          }`}>
                            {control.condition}
                          </div>
                          {/* Citation + expand source */}
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {control.pdf_url ? (
                              <a
                                href={control.pdf_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-teal-600 hover:text-teal-800 font-mono flex items-center gap-0.5"
                                title={`View in PDF${control.pdf_page ? ` (page ${control.pdf_page})` : ''}`}
                              >
                                {control.section_ref}
                                <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            ) : (
                              <span className="text-xs text-gray-400 font-mono">
                                {control.section_ref}
                              </span>
                            )}
                            {control.source_text && (
                              <button
                                onClick={() => setExpandedSource(isSourceExpanded ? null : rowKey)}
                                className="ml-1 text-gray-300 hover:text-gray-500"
                                title="Show source text"
                              >
                                <FileText className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                        {/* Expanded source text + formal citation */}
                        {isSourceExpanded && control.source_text && (
                          <div className="px-3 pb-2 bg-gray-50 border-t border-gray-100">
                            <p className="text-xs text-gray-600 italic mt-1">
                              &ldquo;{control.source_text}&rdquo;
                            </p>
                            {citation && (
                              <p className="text-xs text-gray-400 mt-1 font-mono">
                                {citation}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <p className="text-xs text-gray-400">
            Structured values extracted from the published DCP. Deterministic — same property, same result every time.
          </p>
          {textNotLoadedNote}
        </div>
      )}
    </div>
  );
}

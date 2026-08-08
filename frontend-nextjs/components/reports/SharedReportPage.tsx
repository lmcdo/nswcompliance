'use client';

import { DownloadPdfButton } from './DownloadPdfButton';
import { ToolCrossSell } from './ToolCrossSell';
import { SHARED_REPORT_DISCLAIMER } from '@/lib/disclaimers';

const PRODUCT_LABELS: Record<string, string> = {
  flood: 'Flood Truth Report',
  shadow: 'Shadow Analysis Report',
  'solar-yield': 'Solar Yield Report',
  bushfire: 'Bushfire Pre-Screen Report',
  'granny-flat': 'Granny Flat Eligibility Report',
  'pre-da-history': 'Site History Report',
  'threat-radar': 'Threat Radar Report',
};

const SEVERITY_COLORS: Record<string, string> = {
  high: 'text-red-700 bg-red-50 border-red-200',
  medium: 'text-amber-700 bg-amber-50 border-amber-200',
  low: 'text-green-700 bg-green-50 border-green-200',
};

interface Highlight {
  label: string;
  value: string;
  severity?: 'high' | 'medium' | 'low';
  /**
   * Why there is no answer, for a highlight that could not be established.
   *
   * A badge alone cannot carry an absence: "Not assessed" in a pill next to
   * eight real findings still reads as a mild result. When this is set the row
   * renders the sentence underneath, so the reader is told what was tried and
   * that it is neither a pass nor a fail. Copy comes from lib/not-assessed.ts.
   */
  detail?: string;
}

interface Props {
  reportId: string;
  product: string;
  address: string;
  runDate: string;
  confidence?: string;
  /**
   * What was actually checked, when the product can say. Replaces the
   * "Confidence: x" grade for products that have moved off the ladder
   * (granny-flat, 2026-08-06). Products still passing `confidence` render
   * unchanged — this is additive on purpose.
   */
  stateLabel?: string;
  stateDetail?: string;
  generatePath: string;
  highlights: Highlight[];
}

export function SharedReportPage({
  reportId,
  product,
  address,
  runDate,
  confidence,
  stateLabel,
  stateDetail,
  generatePath,
  highlights,
}: Props) {
  const toolKey = product as Parameters<typeof ToolCrossSell>[0]['currentTool'];

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs font-medium text-teal-600 uppercase tracking-wider mb-2">
          {PRODUCT_LABELS[product] ?? 'Property Report'}
        </p>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">{address}</h1>
        <p className="text-sm text-gray-500">
          Generated {runDate}
          {stateLabel
            ? <span> · {stateLabel}</span>
            : confidence && <span> · Confidence: {confidence}</span>}
        </p>
        {stateDetail && (
          <p className="text-xs text-gray-500 mt-1 max-w-xl">{stateDetail}</p>
        )}
      </div>

      {/* Key findings */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Key findings</h2>
        <div className="space-y-3">
          {highlights.map((h) => (
            <div key={h.label}>
              <div className="flex items-start justify-between gap-4">
                <span className="text-sm text-gray-600">{h.label}</span>
                <span
                  className={`text-sm font-medium px-2.5 py-0.5 rounded-full border ${
                    h.severity ? SEVERITY_COLORS[h.severity] : 'text-gray-700 bg-gray-50 border-gray-200'
                  }`}
                >
                  {h.value}
                </span>
              </div>
              {h.detail && (
                <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2">
                  {h.detail}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Download PDF */}
      <div className="rounded-xl border border-teal-200 bg-teal-50 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Download your report</h2>
        <p className="text-xs text-gray-500 mb-3">
          Full PDF with detailed analysis, compliance checklists, professional referrals, and data source citations.
        </p>
        <DownloadPdfButton
          label="Download PDF"
          apiPath={generatePath}
          reportId={reportId}
        />
      </div>

      {/* Share info */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Share this report</h2>
        <p className="text-xs text-gray-500 mb-3">
          Send this link to your builder, certifier, conveyancer, or solicitor.
        </p>
        <div className="flex items-center gap-2">
          <input
            readOnly
            value={typeof window !== 'undefined' ? window.location.href : ''}
            className="flex-1 text-xs bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-600"
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(window.location.href)}
            className="px-3 py-2 text-xs font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 transition-colors"
          >
            Copy
          </button>
        </div>
      </div>

      {/* Cross-sell */}
      <ToolCrossSell currentTool={toolKey} address={address} />

      {/* Disclaimer */}
      <p className="text-xs text-gray-400 text-center mt-8 mb-4">
        {SHARED_REPORT_DISCLAIMER}
        {' '}Report ID: {reportId.slice(0, 8)}
      </p>
    </div>
  );
}

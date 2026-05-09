'use client';

import { DownloadPdfButton } from './DownloadPdfButton';
import { ToolCrossSell } from './ToolCrossSell';

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
}

interface Props {
  reportId: string;
  product: string;
  address: string;
  runDate: string;
  confidence?: string;
  generatePath: string;
  highlights: Highlight[];
}

export function SharedReportPage({
  reportId,
  product,
  address,
  runDate,
  confidence,
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
          {confidence && <span> · Confidence: {confidence}</span>}
        </p>
      </div>

      {/* Key findings */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Key findings</h2>
        <div className="space-y-3">
          {highlights.map((h) => (
            <div key={h.label} className="flex items-start justify-between gap-4">
              <span className="text-sm text-gray-600">{h.label}</span>
              <span
                className={`text-sm font-medium px-2.5 py-0.5 rounded-full border ${
                  h.severity ? SEVERITY_COLORS[h.severity] : 'text-gray-700 bg-gray-50 border-gray-200'
                }`}
              >
                {h.value}
              </span>
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
        This report is indicative only and does not constitute planning, legal, or financial advice.
        Always consult a qualified professional before making decisions.
        Report ID: {reportId.slice(0, 8)}
      </p>
    </div>
  );
}

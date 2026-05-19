'use client';

import { WaitlistButton } from './WaitlistButton';

interface PaywallGateProps {
  tool: 'flood-truth' | 'shadow' | 'solar-yield';
  reportId: string;
  address: string;
  /** Price in AUD, displayed on the CTA. */
  price: number;
  /** Short alarming headline driven by actual result data. */
  alarmHeadline: string;
  /** Supporting detail sentence. */
  alarmDetail: string;
  /** Bullet list of what the paid report contains. */
  previewItems: string[];
}

const TOOL_LABELS: Record<PaywallGateProps['tool'], string> = {
  'flood-truth':  'Flood Truth Report',
  'shadow':       'Shadow Analysis Report',
  'solar-yield':  'Solar Yield Report',
};

export function PaywallGate({
  tool,
  address,
  alarmHeadline,
  alarmDetail,
  previewItems,
}: PaywallGateProps) {
  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">

      {/* Alarm band */}
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">{alarmHeadline}</p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">{alarmDetail}</p>
      </div>

      {/* Blurred preview */}
      <div className="relative bg-white px-5 pt-4 pb-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          What&rsquo;s in the {TOOL_LABELS[tool]}
        </p>
        <ul className="space-y-2">
          {previewItems.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {item}
            </li>
          ))}
        </ul>
        {/* Blur overlay on bottom half */}
        <div
          className="absolute bottom-0 left-0 right-0 h-20 pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, transparent, white)' }}
        />
      </div>

      {/* Waitlist CTA */}
      <div className="bg-white px-5 pb-5 pt-3">
        <WaitlistButton interestType={tool} address={address} />
      </div>
    </div>
  );
}

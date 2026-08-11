/**
 * Regulatory Currency Notice - Global Disclaimer
 * Displays prominent warning that certifiers must verify all provisions
 * For legal liability protection
 */

import React from 'react';

interface RegulatoryCurrencyNoticeProps {
  lastUpdateDate?: string; // ISO date string
  className?: string;
}

export function RegulatoryCurrencyNotice({
  lastUpdateDate,
  className = ''
}: RegulatoryCurrencyNoticeProps) {
  const updateDate = lastUpdateDate
    ? new Date(lastUpdateDate).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      })
    : new Date().toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });

  return (
    <div className={`bg-amber-50 border-2 border-amber-400 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-2xl">
          ⚠️
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-amber-900 uppercase">
            Regulatory Currency Notice
          </h3>
          <div className="mt-2 text-sm text-amber-800 space-y-2">
            <p>
              <strong>Database last updated:</strong> {updateDate}
            </p>
            <p>
              Certifiers must verify all provisions are current before issuing certificates.
              Always check the official sources:
            </p>
            <ul className="list-disc list-inside ml-2 space-y-1">
              <li>
                <strong>SEPPs/LEPs:</strong>{' '}
                <a
                  href="https://legislation.nsw.gov.au"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-amber-900 font-medium"
                >
                  legislation.nsw.gov.au
                </a>
              </li>
              <li>
                <strong>DCPs:</strong>{' '}
                your council&apos;s website
              </li>
            </ul>
            <p className="text-xs mt-3 italic">
              This system accepts no liability for superseded or outdated provisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact version for page footers
 */
export function RegulatoryCurrencyFooter() {
  return (
    <div className="border-t-2 border-gray-300 bg-gray-50 p-4 text-center">
      <p className="text-xs text-gray-600">
        ⚠️ <strong>Regulatory Currency Notice:</strong> All provisions must be verified
        against official sources before final decisions.{' '}
        <a
          href="https://legislation.nsw.gov.au"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-gray-900"
        >
          NSW Legislation
        </a>
        {' | '}
        your council&apos;s website for DCPs
      </p>
    </div>
  );
}

/**
 * Dismissible banner for top of assessment page
 */
export function RegulatoryCurrencyBanner() {
  const [dismissed, setDismissed] = React.useState(false);

  // Check if user has dismissed this banner before (localStorage)
  React.useEffect(() => {
    const isDismissed = localStorage.getItem('regulatory-notice-dismissed');
    if (isDismissed === 'true') {
      setDismissed(true);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem('regulatory-notice-dismissed', 'true');
    setDismissed(true);
  };

  if (dismissed) {
    return null;
  }

  return (
    <div className="bg-amber-100 border-b-2 border-amber-400 p-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <span className="text-xl">⚠️</span>
          {/* prior-art-checked: copy edit to this existing banner component itself, no new capability */}
          <p className="text-sm text-amber-900">
            <strong>Important:</strong> Provisions are shown as published and may be
            superseded. Check{' '}
            <a
              href="https://legislation.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium hover:text-amber-950"
            >
              legislation.nsw.gov.au
            </a>{' '}
            for current SEPPs/LEPs before relying on them.
          </p>
        </div>
        <button
          onClick={handleDismiss}
          className="px-3 py-1 text-sm text-amber-700 hover:text-amber-900 hover:bg-amber-200 rounded"
          aria-label="Dismiss notice"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

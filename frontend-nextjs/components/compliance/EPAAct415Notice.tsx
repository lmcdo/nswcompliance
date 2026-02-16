'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';

/**
 * EPAAct415ComplianceNotice - Collapsible legal disclaimer
 *
 * Ensures users understand EP&A Act s 4.15 compliance obligations.
 * Collapsed by default for returning users, can be dismissed.
 */

export function EPAAct415ComplianceNotice() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // Check if user has seen this before
  useEffect(() => {
    const dismissed = localStorage.getItem('epa-notice-dismissed');
    const hasSeenBefore = localStorage.getItem('epa-notice-seen');

    if (dismissed === 'true') {
      setIsDismissed(true);
    } else if (!hasSeenBefore) {
      // First-time visitor - show expanded
      setIsExpanded(true);
      localStorage.setItem('epa-notice-seen', 'true');
    }
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('epa-notice-dismissed', 'true');
  };

  if (isDismissed) {
    // Minimal persistent reminder
    return (
      <div className="border-l-4 border-blue-400 bg-blue-50/20 px-3 py-2 mb-3">
        <button
          onClick={() => setIsDismissed(false)}
          className="text-xs text-blue-700 hover:underline flex items-center gap-1"
        >
          <span>ℹ️</span>
          <span>Compliance reminder: All provisions must be considered per EP&A Act s 4.15</span>
        </button>
      </div>
    );
  }

  return (
    <div className="border-l-4 border-blue-400 bg-blue-50/30 px-4 py-3 mb-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-base">ℹ️</div>
        <div className="flex-1 min-w-0">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-semibold text-blue-900 hover:text-blue-700 transition-colors w-full text-left"
          >
            <span>EP&A Act s 4.15 - Important compliance information</span>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 flex-shrink-0" />
            ) : (
              <ChevronDown className="h-4 w-4 flex-shrink-0" />
            )}
          </button>

          {isExpanded && (
            <div className="mt-2 text-sm text-blue-800 leading-relaxed">
              <p>
                All provisions shown must be considered when assessing compliance with
                <strong> Environmental Planning and Assessment Act 1979 s 4.15</strong>.
                Priority indicators surface critical requirements first but do not exclude
                any provisions from consideration. Certifiers must review all applicable
                provisions before issuing certificates.
              </p>
            </div>
          )}
        </div>

        <button
          onClick={handleDismiss}
          className="flex-shrink-0 text-blue-600 hover:text-blue-800 transition-colors"
          title="Minimize notice"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

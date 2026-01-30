'use client';

/**
 * EPAAct415ComplianceNotice - Sticky legal disclaimer banner
 *
 * Ensures users understand EP&A Act s 4.15 compliance obligations.
 * Priority indicators surface critical requirements first but do not
 * exclude any provisions from consideration.
 */

export function EPAAct415ComplianceNotice() {
  return (
    <div className="sticky top-0 z-10 bg-blue-50 border-b-2 border-blue-400 px-4 py-3 mb-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-xl">ℹ️</div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-blue-900 uppercase mb-1">
            EP&A Act s 4.15 Compliance Notice
          </h3>
          <p className="text-sm text-blue-800 leading-relaxed">
            All provisions shown must be considered when assessing compliance with
            <strong> Environmental Planning and Assessment Act 1979 s 4.15</strong>.
            Priority indicators surface critical requirements first but do not exclude
            any provisions from consideration. Certifiers must review all applicable
            provisions before issuing certificates.
          </p>
        </div>
      </div>
    </div>
  );
}

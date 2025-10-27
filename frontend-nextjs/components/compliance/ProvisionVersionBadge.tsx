/**
 * Provision Version Badge Component
 * Displays version metadata for certifier legal compliance
 * Shows regulation year, amendments, and staleness warnings
 */

import React from 'react';
import type { ProvisionVersionMetadata } from '@/types/provision-search';

interface ProvisionVersionBadgeProps {
  version: ProvisionVersionMetadata;
  compact?: boolean; // Compact mode for search results
}

export function ProvisionVersionBadge({ version, compact = false }: ProvisionVersionBadgeProps) {
  // Determine badge styling based on staleness
  const stalenessStyles = {
    current: 'bg-green-50 text-green-700 border-green-200',
    caution: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    stale: 'bg-red-50 text-red-700 border-red-200'
  };

  const stalenessIcons = {
    current: '✓',
    caution: '⚠️',
    stale: '🚨'
  };

  const badgeStyle = stalenessStyles[version.staleness_level];
  const icon = stalenessIcons[version.staleness_level];

  if (compact) {
    // Compact mode for search results lists
    return (
      <div className="flex items-center gap-2 text-sm">
        {version.regulation_year && (
          <span className="text-gray-600 font-medium">
            {version.regulation_year}
          </span>
        )}
        {version.amendment_reference && (
          <span className="text-gray-500 text-xs">
            ({version.amendment_reference})
          </span>
        )}
        {version.staleness_level !== 'current' && (
          <span className={`px-2 py-0.5 rounded text-xs ${badgeStyle}`}>
            {icon} {version.staleness_level === 'caution' ? 'Verify' : 'Stale'}
          </span>
        )}
      </div>
    );
  }

  // Full mode for provision cards
  return (
    <div className={`border rounded-lg p-3 ${badgeStyle}`}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="font-semibold text-sm flex items-center gap-2">
            {icon} Version Information
          </div>

          <div className="text-sm space-y-0.5">
            {version.regulation_year && (
              <div>
                <span className="font-medium">Regulation:</span>{' '}
                {version.regulation_year}
              </div>
            )}

            {version.amendment_reference && (
              <div>
                <span className="font-medium">Amendment:</span>{' '}
                {version.amendment_reference}
                {version.amendment_date && (
                  <span className="text-xs ml-1">
                    ({new Date(version.amendment_date).toLocaleDateString('en-AU', {
                      month: 'short',
                      year: 'numeric'
                    })})
                  </span>
                )}
              </div>
            )}

            <div>
              <span className="font-medium">Last Verified:</span>{' '}
              {version.days_since_verified === 0
                ? 'Today'
                : `${version.days_since_verified} days ago`}
            </div>

            <div>
              <span className="font-medium">Status:</span>{' '}
              <span className="uppercase text-xs">
                {version.version_status}
              </span>
            </div>
          </div>
        </div>
      </div>

      {version.staleness_level === 'stale' && (
        <div className="mt-3 pt-3 border-t border-red-300">
          <p className="text-xs font-medium">
            ⚠️ CERTIFIER NOTE:
          </p>
          <p className="text-xs mt-1">
            This provision has not been verified in over 60 days.
            Please verify against current version before relying on it.
          </p>
        </div>
      )}

      {version.staleness_level === 'caution' && (
        <div className="mt-2 text-xs">
          Consider verifying against current version.
        </div>
      )}
    </div>
  );
}

/**
 * Compact version badge for inline display in search results
 */
export function ProvisionVersionInline({ version }: { version: ProvisionVersionMetadata }) {
  // Badge styling based on staleness
  const badgeStyles = {
    current: 'bg-green-50 text-green-700 border-green-300',
    caution: 'bg-yellow-50 text-yellow-700 border-yellow-300',
    stale: 'bg-red-50 text-red-700 border-red-300'
  };

  const icons = {
    current: '✓',
    caution: '⚠️',
    stale: '🚨'
  };

  const badgeStyle = badgeStyles[version.staleness_level];
  const icon = icons[version.staleness_level];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${badgeStyle}`}>
      <span>{icon}</span>
      {version.regulation_year && (
        <span>{version.regulation_year}</span>
      )}
      {version.amendment_reference && (
        <span>• {version.amendment_reference}</span>
      )}
      {version.staleness_level !== 'current' && (
        <span className="text-[10px] uppercase">
          {version.staleness_level === 'caution' ? 'Verify' : 'Stale'}
        </span>
      )}
      {version.days_since_verified > 30 && (
        <span className="text-[10px]">
          ({version.days_since_verified}d)
        </span>
      )}
    </span>
  );
}

/**
 * Staleness warning banner for stale provisions
 */
export function StalenessWarning({ version }: { version: ProvisionVersionMetadata }) {
  if (version.staleness_level !== 'stale') {
    return null;
  }

  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <span className="text-2xl">🚨</span>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            VERSION CURRENCY WARNING
          </h3>
          <div className="mt-2 text-sm text-red-700 space-y-1">
            <p>
              This provision was last imported <strong>{version.days_since_verified} days ago</strong>.
              Regulations may have been amended since then.
            </p>
            <p className="font-medium mt-2">REQUIRED ACTION:</p>
            <ul className="list-disc list-inside ml-2 space-y-0.5">
              <li>Verify current version at NSW Legislation website</li>
              <li>Check for any gazetted amendments</li>
              <li>Document verification in your assessment notes</li>
            </ul>
          </div>
          <div className="mt-3 flex gap-2">
            <a
              href="https://legislation.nsw.gov.au"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-red-800 hover:text-red-900 underline"
            >
              Verify on NSW Legislation →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

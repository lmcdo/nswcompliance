'use client';

/**
 * CdcComplianceResults Component
 *
 * Displays the results of CDC compliance checking with per-field status,
 * next steps section, and disclaimer footer.
 */

import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  FileText,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { FormValidation, CDC_STANDARDS, getRequiredParking } from './types';

interface CdcComplianceResultsProps {
  /** Validation state from form */
  validation: FormValidation;
  /** Number of passing checks */
  passCount: number;
  /** Total number of checks */
  totalChecks: number;
  /** Number of bedrooms (for parking requirement display) */
  bedrooms: number;
}

/**
 * Single result row
 */
function ResultRow({
  label,
  proposed,
  required,
  valid,
  margin,
  unit,
  isMax = false,
}: {
  label: string;
  proposed: number;
  required: number;
  valid: boolean;
  margin: number;
  unit: string;
  isMax?: boolean;
}) {
  const comparison = isMax ? '\u2264' : '\u2265'; // ≤ or ≥
  const marginPrefix = margin >= 0 ? '+' : '';

  return (
    <div
      className={`flex items-center justify-between py-2 px-3 rounded-lg ${
        valid ? 'bg-green-50' : 'bg-red-50'
      }`}
    >
      <div className="flex items-center gap-2">
        {valid ? (
          <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
        ) : (
          <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
        )}
        <span className={`text-sm ${valid ? 'text-green-800' : 'text-red-800'}`}>
          {label}: {proposed}{unit} {comparison} {required}{unit}
        </span>
      </div>
      <Badge
        variant="outline"
        className={`text-xs ${
          valid
            ? 'bg-green-100 text-green-700 border-green-300'
            : 'bg-red-100 text-red-700 border-red-300'
        }`}
      >
        [{marginPrefix}{Math.abs(margin).toFixed(1)}{unit}]
      </Badge>
    </div>
  );
}

export function CdcComplianceResults({
  validation,
  passCount,
  totalChecks,
  bedrooms,
}: CdcComplianceResultsProps) {
  const allPass = passCount === totalChecks;
  const mostPass = passCount >= totalChecks - 2;
  const failedChecks = Object.entries(validation).filter(([, v]) => !v.valid);

  // Get status color classes
  const statusClasses = allPass
    ? 'bg-green-100 text-green-800 border-green-300'
    : mostPass
    ? 'bg-amber-100 text-amber-800 border-amber-300'
    : 'bg-red-100 text-red-800 border-red-300';

  const statusLabel = allPass
    ? 'LIKELY COMPLIANT'
    : mostPass
    ? `${totalChecks - passCount} ISSUE${totalChecks - passCount > 1 ? 'S' : ''}`
    : 'NON-COMPLIANT';

  return (
    <div className="space-y-4">
      {/* Results Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">RESULTS</span>
        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium ${statusClasses}`}
        >
          {allPass ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : mostPass ? (
            <AlertTriangle className="w-4 h-4" />
          ) : (
            <XCircle className="w-4 h-4" />
          )}
          {passCount}/{totalChecks} {statusLabel}
        </div>
      </div>

      {/* Individual Results */}
      <div className="space-y-2">
        <ResultRow
          label="Front"
          proposed={validation.front.proposed}
          required={validation.front.required}
          valid={validation.front.valid}
          margin={validation.front.margin}
          unit="m"
        />
        <ResultRow
          label="Side Left"
          proposed={validation.sideLeft.proposed}
          required={validation.sideLeft.required}
          valid={validation.sideLeft.valid}
          margin={validation.sideLeft.margin}
          unit="m"
        />
        <ResultRow
          label="Side Right"
          proposed={validation.sideRight.proposed}
          required={validation.sideRight.required}
          valid={validation.sideRight.valid}
          margin={validation.sideRight.margin}
          unit="m"
        />
        <ResultRow
          label="Rear"
          proposed={validation.rear.proposed}
          required={validation.rear.required}
          valid={validation.rear.valid}
          margin={validation.rear.margin}
          unit="m"
        />
        <ResultRow
          label="Site coverage"
          proposed={validation.siteCoverage.proposed}
          required={validation.siteCoverage.required}
          valid={validation.siteCoverage.valid}
          margin={validation.siteCoverage.margin}
          unit="%"
          isMax
        />
        <ResultRow
          label="Landscaped"
          proposed={validation.landscapedArea.proposed}
          required={validation.landscapedArea.required}
          valid={validation.landscapedArea.valid}
          margin={validation.landscapedArea.margin}
          unit="%"
        />
        <ResultRow
          label="Height"
          proposed={validation.buildingHeight.proposed}
          required={validation.buildingHeight.required}
          valid={validation.buildingHeight.valid}
          margin={validation.buildingHeight.margin}
          unit="m"
          isMax
        />
        <ResultRow
          label="Storeys"
          proposed={validation.storeys.proposed}
          required={validation.storeys.required}
          valid={validation.storeys.valid}
          margin={validation.storeys.margin}
          unit=""
          isMax
        />
        <ResultRow
          label="Parking"
          proposed={validation.parking.proposed}
          required={getRequiredParking(bedrooms)}
          valid={validation.parking.valid}
          margin={validation.parking.margin}
          unit=""
        />
      </div>

      {/* Next Steps for Failed Checks */}
      {failedChecks.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2 text-amber-800 font-medium text-sm">
            <AlertTriangle className="w-4 h-4" />
            Action Required
          </div>
          <ul className="space-y-1.5 text-sm text-amber-700">
            {failedChecks.map(([key, value]) => {
              const fieldName = getFieldLabel(key);
              const shortfall = Math.abs(value.margin);
              const unit = getFieldUnit(key);

              return (
                <li key={key} className="flex items-start gap-2">
                  <ArrowRight className="w-3 h-3 mt-1 flex-shrink-0" />
                  <span>
                    <strong>{fieldName}</strong>: Increase by {shortfall.toFixed(1)}{unit} or lodge Development Application
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* All Pass Message */}
      {allPass && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-start gap-2 text-green-800 text-sm">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium">
                All standards met for CDC pathway
              </div>
              <p className="text-green-700 mt-1">
                Based on the values entered, this development may be suitable for a Complying Development Certificate.
                Engage a registered certifier to proceed.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Disclaimer Footer */}
      <div className="bg-gray-100 rounded-lg p-3 space-y-2">
        <div className="flex items-center gap-2 text-gray-600 text-xs font-medium">
          <FileText className="w-4 h-4" />
          DISCLAIMER
        </div>
        <p className="text-xs text-gray-600 leading-relaxed">
          This is for general guidance only. Actual requirements may vary based on site
          conditions, easements, covenants, and council-specific controls. The values shown
          are based on SEPP (Housing) 2021 default standards for new dwelling houses in
          residential zones. Always engage a registered certifier before proceeding with
          any development application.
        </p>
        <p className="text-xs text-gray-500">
          Reference: State Environmental Planning Policy (Housing) 2021, Part 3, Division 1
        </p>
      </div>
    </div>
  );
}

/**
 * Get human-readable label for a validation field key
 */
function getFieldLabel(key: string): string {
  const labels: Record<string, string> = {
    front: 'Front setback',
    sideLeft: 'Side Left setback',
    sideRight: 'Side Right setback',
    rear: 'Rear setback',
    siteCoverage: 'Site coverage',
    landscapedArea: 'Landscaped area',
    buildingHeight: 'Building height',
    storeys: 'Storeys',
    parking: 'Parking spaces',
  };
  return labels[key] || key;
}

/**
 * Get unit for a validation field key
 */
function getFieldUnit(key: string): string {
  const units: Record<string, string> = {
    front: 'm',
    sideLeft: 'm',
    sideRight: 'm',
    rear: 'm',
    siteCoverage: '%',
    landscapedArea: '%',
    buildingHeight: 'm',
    storeys: '',
    parking: ' space(s)',
  };
  return units[key] || '';
}

export default CdcComplianceResults;

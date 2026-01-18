'use client';

/**
 * CdcComplianceResults Component
 *
 * Displays CDC compliance results with minimal color usage.
 * Only pass/fail icons use color; rest is typography-driven.
 */

import {
  Check,
  X,
  ArrowRight,
  FileText,
} from 'lucide-react';
import { FormValidation, getRequiredParking } from './types';

interface CdcComplianceResultsProps {
  validation: FormValidation;
  passCount: number;
  totalChecks: number;
  bedrooms: number;
}

/**
 * Single result row - clean, minimal
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
  const comparison = isMax ? '≤' : '≥';
  const marginPrefix = margin >= 0 ? '+' : '';

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        {valid ? (
          <Check className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
        ) : (
          <X className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
        )}
        <span className="text-sm text-gray-700">
          {label}
        </span>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <span className={valid ? 'text-gray-600' : 'text-red-600 font-medium'}>
          {proposed}{unit} {comparison} {required}{unit}
        </span>
        <span className="text-xs text-gray-400 w-12 text-right">
          [{marginPrefix}{Math.abs(margin).toFixed(1)}{unit}]
        </span>
      </div>
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
  const failedChecks = Object.entries(validation).filter(([, v]) => !v.valid);

  return (
    <div className="space-y-4">
      {/* Results Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Results
        </span>
        <span className={`text-sm font-medium ${allPass ? 'text-green-700' : 'text-gray-600'}`}>
          {allPass ? (
            <span className="inline-flex items-center gap-1">
              <Check className="w-4 h-4" />
              {passCount}/{totalChecks} COMPLIANT
            </span>
          ) : (
            `${passCount}/${totalChecks} pass`
          )}
        </span>
      </div>

      {/* Individual Results */}
      <div className="bg-gray-50 rounded p-3">
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

      {/* Action Required - only if failures */}
      {failedChecks.length > 0 && (
        <div className="text-sm space-y-1.5">
          <div className="text-gray-600 font-medium">Action Required:</div>
          {failedChecks.map(([key, value]) => {
            const fieldName = getFieldLabel(key);
            const shortfall = Math.abs(value.margin);
            const unit = getFieldUnit(key);

            return (
              <div key={key} className="flex items-start gap-2 text-gray-600">
                <ArrowRight className="w-3 h-3 mt-1 flex-shrink-0 text-gray-400" />
                <span>
                  {fieldName}: adjust by {shortfall.toFixed(1)}{unit}, or lodge DA
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* All Pass Message */}
      {allPass && (
        <div className="text-sm text-gray-600 bg-gray-50 rounded p-3">
          <div className="flex items-start gap-2">
            <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-medium text-gray-700">All standards met for CDC pathway.</span>
              <span className="text-gray-500"> Engage a registered certifier to proceed.</span>
            </div>
          </div>
        </div>
      )}

      {/* Disclaimer Footer */}
      <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-100">
        <div className="flex items-center gap-1.5">
          <FileText className="w-3 h-3" />
          <span className="font-medium">Disclaimer</span>
        </div>
        <p className="leading-relaxed">
          General guidance only. Requirements may vary based on site conditions,
          easements, and council controls. Based on SEPP Housing 2021 Part 3 Division 1.
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
    sideLeft: 'Side Left',
    sideRight: 'Side Right',
    rear: 'Rear setback',
    siteCoverage: 'Site coverage',
    landscapedArea: 'Landscaped area',
    buildingHeight: 'Height',
    storeys: 'Storeys',
    parking: 'Parking',
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

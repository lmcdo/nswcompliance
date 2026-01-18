'use client';

/**
 * CdcFieldGroup Component
 *
 * Reusable input field with real-time validation badge.
 * Shows pass/fail status and margin for CDC compliance checks.
 */

import { CheckCircle2, XCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FieldValidation } from './types';

interface CdcFieldGroupProps {
  /** Field label */
  label: string;
  /** Field name/id */
  name: string;
  /** Current value */
  value: number;
  /** Validation state */
  validation: FieldValidation;
  /** Change handler */
  onChange: (value: number) => void;
  /** Unit label (e.g., "m", "%") */
  unit?: string;
  /** Helper text showing requirement */
  helperText?: string;
  /** Step for number input */
  step?: number;
  /** Minimum input value */
  min?: number;
  /** Maximum input value */
  max?: number;
  /** Disable input */
  disabled?: boolean;
  /** Compact mode */
  compact?: boolean;
}

export function CdcFieldGroup({
  label,
  name,
  value,
  validation,
  onChange,
  unit = '',
  helperText,
  step = 0.1,
  min = 0,
  max = 100,
  disabled = false,
  compact = false,
}: CdcFieldGroupProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const num = parseFloat(e.target.value);
    if (!isNaN(num)) {
      onChange(num);
    }
  };

  const { valid, required, margin, message } = validation;

  return (
    <div className={compact ? 'space-y-1' : 'space-y-1.5'}>
      <div className="flex items-center justify-between">
        <Label
          htmlFor={name}
          className={`text-xs font-medium ${
            valid ? 'text-gray-700' : 'text-red-700'
          }`}
        >
          {label}
        </Label>
        <div className="flex items-center gap-1">
          {valid ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
        </div>
      </div>

      <div className="relative">
        <Input
          id={name}
          name={name}
          type="number"
          value={value}
          onChange={handleChange}
          step={step}
          min={min}
          max={max}
          disabled={disabled}
          className={`pr-8 h-9 text-sm ${
            valid
              ? 'border-green-300 focus:border-green-500 focus:ring-green-500'
              : 'border-red-300 focus:border-red-500 focus:ring-red-500'
          }`}
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">
            {unit}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">
          {helperText || `Min ${required}${unit}`}
        </span>
        {!valid && margin < 0 && (
          <span className="text-red-600 font-medium">
            {Math.abs(margin).toFixed(1)}{unit} short
          </span>
        )}
        {valid && margin > 0 && (
          <span className="text-green-600">
            +{margin.toFixed(1)}{unit}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Compact inline field for use in rows
 */
export function CdcFieldInline({
  label,
  name,
  value,
  validation,
  onChange,
  unit = '',
  step = 0.1,
  min = 0,
  max = 100,
}: Omit<CdcFieldGroupProps, 'helperText' | 'disabled' | 'compact'>) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const num = parseFloat(e.target.value);
    if (!isNaN(num)) {
      onChange(num);
    }
  };

  const { valid, required, margin } = validation;

  return (
    <div className="flex flex-col items-center gap-1">
      <Label htmlFor={name} className="text-xs text-gray-600 font-medium">
        {label}
      </Label>
      <div className="relative">
        <Input
          id={name}
          name={name}
          type="number"
          value={value}
          onChange={handleChange}
          step={step}
          min={min}
          max={max}
          className={`w-20 h-8 text-center text-sm pr-1 ${
            valid
              ? 'border-green-300 bg-green-50'
              : 'border-red-300 bg-red-50'
          }`}
        />
        <span className="absolute -right-4 top-1/2 -translate-y-1/2">
          {valid ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
        </span>
      </div>
      <span className="text-[10px] text-gray-500">
        Min {required}{unit}
      </span>
      {!valid && (
        <span className="text-[10px] text-red-600 font-medium">
          {Math.abs(margin).toFixed(1)}{unit} short
        </span>
      )}
    </div>
  );
}

export default CdcFieldGroup;

'use client';

/**
 * CdcFieldGroup Component
 *
 * Reusable input field with real-time validation.
 * Uses minimal color - only small icons for pass/fail.
 */

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FieldValidation } from './types';
import { StatusIcon, StandardHint } from './CdcCheckBits';

interface CdcFieldGroupProps {
  label: string;
  name: string;
  value: number | null;
  validation: FieldValidation;
  onChange: (value: number | null) => void;
  unit?: string;
  helperText?: string;
  step?: number;
  min?: number;
  max?: number;
  disabled?: boolean;
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
    onChange(Number.isNaN(num) ? null : num);
  };

  const { status, margin } = validation;

  return (
    <div className={compact ? 'space-y-1' : 'space-y-1.5'}>
      <div className="flex items-center justify-between">
        <Label htmlFor={name} className="text-xs font-medium text-gray-600">
          {label}
        </Label>
        <StatusIcon status={status} />
      </div>

      <div className="relative">
        <Input
          id={name}
          name={name}
          type="number"
          value={value ?? ''}
          onChange={handleChange}
          step={step}
          min={min}
          max={max}
          disabled={disabled}
          className="pr-8 h-9 text-sm"
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">
            {unit}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">
          {helperText ?? <StandardHint check={validation} className="" />}
        </span>
        {status === 'fail' && margin !== null && margin < 0 && (
          <span className="text-red-500 font-medium">
            {Math.abs(margin).toFixed(1)}{unit} short
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
    onChange(Number.isNaN(num) ? null : num);
  };

  const { status, margin } = validation;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <Label htmlFor={name} className="text-xs text-gray-500">
          {label}
        </Label>
        <StatusIcon status={status} small />
      </div>
      <div className="relative">
        <Input
          id={name}
          name={name}
          type="number"
          value={value ?? ''}
          onChange={handleChange}
          step={step}
          min={min}
          max={max}
          className="h-8 text-sm pr-5"
        />
        {unit && (
          <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
            {unit}
          </span>
        )}
      </div>
      <div className="text-[10px] text-gray-400">
        <StandardHint check={validation} className="" />
        {status === 'fail' && margin !== null && margin < 0 && (
          <span className="text-red-500 ml-1">
            ({Math.abs(margin).toFixed(1)} short)
          </span>
        )}
      </div>
    </div>
  );
}

export default CdcFieldGroup;

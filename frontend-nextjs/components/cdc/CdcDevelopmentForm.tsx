'use client';

/**
 * CdcDevelopmentForm Component
 *
 * Form for entering proposed development details for CDC compliance checking.
 * Uses neutral styling with minimal color - only green/red for pass/fail icons.
 */

import { Check, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CdcFieldInline } from './CdcFieldGroup';
import {
  CdcComplianceInput,
  CdcDevelopmentType,
  DEVELOPMENT_TYPE_OPTIONS,
  FormValidation,
  getRequiredParking,
} from './types';

interface CdcDevelopmentFormProps {
  form: CdcComplianceInput;
  validation: FormValidation;
  updateField: <K extends keyof CdcComplianceInput>(
    field: K,
    value: CdcComplianceInput[K]
  ) => void;
  updateSetback: (
    field: 'front' | 'sideLeft' | 'sideRight' | 'rear',
    value: number
  ) => void;
  passCount: number;
  totalChecks: number;
}

export function CdcDevelopmentForm({
  form,
  validation,
  updateField,
  updateSetback,
  passCount,
  totalChecks,
}: CdcDevelopmentFormProps) {
  return (
    <div className="space-y-4">
      {/* Development Type */}
      <div className="space-y-1.5">
        <Label htmlFor="developmentType" className="text-xs font-medium text-gray-600">
          Development Type
        </Label>
        <Select
          value={form.developmentType}
          onValueChange={(value: CdcDevelopmentType) =>
            updateField('developmentType', value)
          }
        >
          <SelectTrigger id="developmentType" className="w-full h-9 text-sm">
            <SelectValue placeholder="Select development type" />
          </SelectTrigger>
          <SelectContent>
            {DEVELOPMENT_TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Setbacks Row */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-gray-600">
          Setbacks (meters)
        </Label>
        <div className="grid grid-cols-4 gap-2">
          <CdcFieldInline
            label="Front"
            name="setback-front"
            value={form.setbacks.front}
            validation={validation.front}
            onChange={(v) => updateSetback('front', v)}
            unit="m"
            step={0.1}
            min={0}
            max={50}
          />
          <CdcFieldInline
            label="Side L"
            name="setback-side-left"
            value={form.setbacks.sideLeft}
            validation={validation.sideLeft}
            onChange={(v) => updateSetback('sideLeft', v)}
            unit="m"
            step={0.1}
            min={0}
            max={50}
          />
          <CdcFieldInline
            label="Side R"
            name="setback-side-right"
            value={form.setbacks.sideRight}
            validation={validation.sideRight}
            onChange={(v) => updateSetback('sideRight', v)}
            unit="m"
            step={0.1}
            min={0}
            max={50}
          />
          <CdcFieldInline
            label="Rear"
            name="setback-rear"
            value={form.setbacks.rear}
            validation={validation.rear}
            onChange={(v) => updateSetback('rear', v)}
            unit="m"
            step={0.1}
            min={0}
            max={50}
          />
        </div>
      </div>

      {/* Upper Floor Checkbox */}
      <div className="flex items-start gap-2 bg-gray-50 p-2.5 rounded">
        <Checkbox
          id="hasUpperFloorHabitableRooms"
          checked={form.hasUpperFloorHabitableRooms}
          onCheckedChange={(checked) =>
            updateField('hasUpperFloorHabitableRooms', checked === true)
          }
          className="mt-0.5"
        />
        <div>
          <Label
            htmlFor="hasUpperFloorHabitableRooms"
            className="text-sm text-gray-700 cursor-pointer"
          >
            Upper floor habitable rooms face rear
          </Label>
          <p className="text-xs text-gray-500">
            Increases rear setback to 6.0m
          </p>
        </div>
      </div>

      {/* Site Coverage & Landscaping */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="siteCoverage" className="text-xs font-medium text-gray-600">
              Site Coverage
            </Label>
            {validation.siteCoverage.valid ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
          <div className="relative">
            <Input
              id="siteCoverage"
              type="number"
              value={form.siteCoveragePercent}
              onChange={(e) =>
                updateField('siteCoveragePercent', parseFloat(e.target.value) || 0)
              }
              min={0}
              max={100}
              step={1}
              className="pr-7 h-9 text-sm"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              %
            </span>
          </div>
          <span className="text-xs text-gray-400">Max 50%</span>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="landscapedArea" className="text-xs font-medium text-gray-600">
              Landscaped Area
            </Label>
            {validation.landscapedArea.valid ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
          <div className="relative">
            <Input
              id="landscapedArea"
              type="number"
              value={form.landscapedAreaPercent}
              onChange={(e) =>
                updateField('landscapedAreaPercent', parseFloat(e.target.value) || 0)
              }
              min={0}
              max={100}
              step={1}
              className="pr-7 h-9 text-sm"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              %
            </span>
          </div>
          <span className="text-xs text-gray-400">Min 30%</span>
        </div>
      </div>

      {/* Height, Storeys, Bedrooms, Parking */}
      <div className="grid grid-cols-4 gap-2">
        {/* Height */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="height" className="text-xs font-medium text-gray-600">
              Height
            </Label>
            {validation.buildingHeight.valid ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
          <div className="relative">
            <Input
              id="height"
              type="number"
              value={form.buildingHeightMeters}
              onChange={(e) =>
                updateField('buildingHeightMeters', parseFloat(e.target.value) || 0)
              }
              min={0}
              max={20}
              step={0.1}
              className="pr-5 h-9 text-sm"
            />
            <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              m
            </span>
          </div>
          <span className="text-xs text-gray-400">Max 8.5m</span>
        </div>

        {/* Storeys */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="storeys" className="text-xs font-medium text-gray-600">
              Storeys
            </Label>
            {validation.storeys.valid ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
          <Select
            value={String(form.storeys)}
            onValueChange={(value) => updateField('storeys', parseInt(value))}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-gray-400">Max 2</span>
        </div>

        {/* Bedrooms */}
        <div className="space-y-1">
          <Label htmlFor="bedrooms" className="text-xs font-medium text-gray-600">
            Beds
          </Label>
          <Select
            value={String(form.bedrooms)}
            onValueChange={(value) => updateField('bedrooms', parseInt(value))}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
              <SelectItem value="4">4</SelectItem>
              <SelectItem value="5">5+</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-gray-400">For parking</span>
        </div>

        {/* Parking */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="parking" className="text-xs font-medium text-gray-600">
              Parking
            </Label>
            {validation.parking.valid ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <X className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
          <Select
            value={String(form.parkingSpaces)}
            onValueChange={(value) => updateField('parkingSpaces', parseInt(value))}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">0</SelectItem>
              <SelectItem value="1">1</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
              <SelectItem value="4">4+</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-gray-400">
            Min {getRequiredParking(form.bedrooms)}
          </span>
        </div>
      </div>

      {/* Summary - minimal */}
      <div className="flex items-center justify-center py-1">
        <span className="text-sm text-gray-600">
          {passCount === totalChecks ? (
            <span className="inline-flex items-center gap-1.5 text-green-700">
              <Check className="w-4 h-4" />
              {passCount}/{totalChecks} checks pass
            </span>
          ) : (
            <span className="text-gray-500">
              {passCount}/{totalChecks} checks pass
            </span>
          )}
        </span>
      </div>
    </div>
  );
}

export default CdcDevelopmentForm;

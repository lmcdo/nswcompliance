'use client';

/**
 * CdcDevelopmentForm Component
 *
 * Form for entering proposed development details for CDC compliance checking.
 * Every number starts blank. Required figures shown beside each field come from
 * the stored Housing Code standards (with their clause); when none applies the
 * field shows "Not checked".
 */

import { Check } from 'lucide-react';
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
import { StatusIcon, StandardHint } from './CdcCheckBits';
import {
  CdcComplianceInput,
  CdcDevelopmentType,
  DEVELOPMENT_TYPE_OPTIONS,
  FormValidation,
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
    value: number | null
  ) => void;
  passCount: number;
  totalChecks: number;
  notCheckedCount?: number;
}

function parseOrNull(raw: string): number | null {
  const n = parseFloat(raw);
  return Number.isNaN(n) ? null : n;
}

export function CdcDevelopmentForm({
  form,
  validation,
  updateField,
  updateSetback,
  passCount,
  totalChecks,
  notCheckedCount = 0,
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

      {/* Lot facts that select the stored band */}
      <div className="space-y-2">
        <Label className="text-xs font-medium text-gray-600">
          Lot (selects the stored standard)
        </Label>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="lotArea" className="text-xs text-gray-500">
              Lot area
            </Label>
            <div className="relative">
              <Input
                id="lotArea"
                type="number"
                value={form.lotAreaM2 ?? ''}
                onChange={(e) => updateField('lotAreaM2', parseOrNull(e.target.value))}
                min={0}
                step={1}
                className="h-8 text-sm pr-8"
              />
              <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">m²</span>
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="lotWidth" className="text-xs text-gray-500">
              Lot width at building line
            </Label>
            <div className="relative">
              <Input
                id="lotWidth"
                type="number"
                value={form.lotWidthM ?? ''}
                onChange={(e) => updateField('lotWidthM', parseOrNull(e.target.value))}
                min={0}
                step={0.1}
                className="h-8 text-sm pr-5"
              />
              <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">m</span>
            </div>
          </div>
        </div>
      </div>

      {/* Front setback rule depends on neighbouring dwellings */}
      <div className="space-y-2">
        <Label htmlFor="neighbourDwellings" className="text-xs font-medium text-gray-600">
          Are there at least 2 dwelling houses on the same side of the primary road within 40 m?
        </Label>
        <div className="grid grid-cols-2 gap-2">
          <Select
            value={form.neighbourDwellings ?? ''}
            onValueChange={(v) => updateField('neighbourDwellings', v as 'yes' | 'no' | 'unknown')}
          >
            <SelectTrigger id="neighbourDwellings" className="h-8 text-sm">
              <SelectValue placeholder="Select" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="yes">Yes</SelectItem>
              <SelectItem value="no">No</SelectItem>
              <SelectItem value="unknown">Do not know</SelectItem>
            </SelectContent>
          </Select>
          {form.neighbourDwellings === 'yes' && (
            <div className="relative">
              <Input
                id="neighbourAverageFront"
                aria-label="Average front setback of the 2 nearest dwelling houses"
                placeholder="Their average front setback"
                type="number"
                value={form.neighbourAverageFrontM ?? ''}
                onChange={(e) => updateField('neighbourAverageFrontM', parseOrNull(e.target.value))}
                min={0}
                step={0.1}
                className="h-8 text-sm pr-5"
              />
              <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">m</span>
            </div>
          )}
        </div>
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
            The rear setback is then not checked: the stored upper-level bands are not applied.
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
            <StatusIcon status={validation.siteCoverage.status} />
          </div>
          <div className="relative">
            <Input
              id="siteCoverage"
              type="number"
              value={form.siteCoveragePercent ?? ''}
              onChange={(e) => updateField('siteCoveragePercent', parseOrNull(e.target.value))}
              min={0}
              max={100}
              step={1}
              className="pr-7 h-9 text-sm"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              %
            </span>
          </div>
          <StandardHint check={validation.siteCoverage} />
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="landscapedArea" className="text-xs font-medium text-gray-600">
              Landscaped Area
            </Label>
            <StatusIcon status={validation.landscapedArea.status} />
          </div>
          <div className="relative">
            <Input
              id="landscapedArea"
              type="number"
              value={form.landscapedAreaPercent ?? ''}
              onChange={(e) => updateField('landscapedAreaPercent', parseOrNull(e.target.value))}
              min={0}
              max={100}
              step={1}
              className="pr-7 h-9 text-sm"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              %
            </span>
          </div>
          <StandardHint check={validation.landscapedArea} />
        </div>
      </div>

      {/* Height, Storeys, Parking */}
      <div className="grid grid-cols-3 gap-2">
        {/* Height */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="height" className="text-xs font-medium text-gray-600">
              Height
            </Label>
            <StatusIcon status={validation.buildingHeight.status} />
          </div>
          <div className="relative">
            <Input
              id="height"
              type="number"
              value={form.buildingHeightMeters ?? ''}
              onChange={(e) => updateField('buildingHeightMeters', parseOrNull(e.target.value))}
              min={0}
              max={20}
              step={0.1}
              className="pr-5 h-9 text-sm"
            />
            <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">
              m
            </span>
          </div>
          <StandardHint check={validation.buildingHeight} />
        </div>

        {/* Storeys */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="storeys" className="text-xs font-medium text-gray-600">
              Storeys
            </Label>
            <StatusIcon status={validation.storeys.status} />
          </div>
          <Select
            value={form.storeys == null ? '' : String(form.storeys)}
            onValueChange={(value) => updateField('storeys', parseInt(value))}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue placeholder="Select" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
            </SelectContent>
          </Select>
          <StandardHint check={validation.storeys} />
        </div>

        {/* Parking */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="parking" className="text-xs font-medium text-gray-600">
              Parking
            </Label>
            <StatusIcon status={validation.parking.status} />
          </div>
          <Select
            value={form.parkingSpaces == null ? '' : String(form.parkingSpaces)}
            onValueChange={(value) => updateField('parkingSpaces', parseInt(value))}
          >
            <SelectTrigger className="h-9 text-sm">
              <SelectValue placeholder="Select" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">0</SelectItem>
              <SelectItem value="1">1</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
              <SelectItem value="4">4+</SelectItem>
            </SelectContent>
          </Select>
          <StandardHint check={validation.parking} />
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
              {notCheckedCount > 0 && `, ${notCheckedCount} not checked`}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}

export default CdcDevelopmentForm;

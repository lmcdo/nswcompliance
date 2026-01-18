/**
 * useCdcComplianceCalculator Hook
 *
 * Form state management and real-time validation for CDC compliance calculator.
 * Uses SEPP Housing 2021 standards for validation.
 */

import { useState, useCallback, useMemo } from 'react';
import { quickValidateSetback } from './useCdcSetbacks';
import {
  CdcComplianceInput,
  CdcComplianceResponse,
  CDC_INPUT_DEFAULTS,
  CDC_STANDARDS,
  FormValidation,
  FieldValidation,
  getRequiredParking,
} from '@/components/cdc/types';

interface UseCdcComplianceCalculatorOptions {
  /** Initial values for the form */
  initialValues?: Partial<CdcComplianceInput>;
}

interface UseCdcComplianceCalculatorReturn {
  /** Form values */
  form: CdcComplianceInput;
  /** Update a form field */
  updateField: <K extends keyof CdcComplianceInput>(
    field: K,
    value: CdcComplianceInput[K]
  ) => void;
  /** Update a setback field */
  updateSetback: (
    field: 'front' | 'sideLeft' | 'sideRight' | 'rear',
    value: number
  ) => void;
  /** Real-time validation state for all fields */
  validation: FormValidation;
  /** Count of passing checks */
  passCount: number;
  /** Total number of checks */
  totalChecks: number;
  /** Whether all checks pass */
  isFullyCompliant: boolean;
  /** Submit form to API */
  submit: (address?: string) => Promise<void>;
  /** API response */
  result: CdcComplianceResponse | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** Reset form to defaults */
  reset: () => void;
}

/**
 * Validate a single numeric field against a maximum
 */
function validateMax(
  proposed: number,
  maximum: number,
  reference: string,
  fieldName: string,
  unit: string
): FieldValidation {
  const valid = proposed <= maximum;
  const margin = maximum - proposed;
  return {
    valid,
    required: maximum,
    proposed,
    margin: Math.round(margin * 100) / 100,
    reference,
    message: valid
      ? margin > 0
        ? `${margin.toFixed(1)}${unit} below max`
        : 'At maximum'
      : `Exceeds max by ${Math.abs(margin).toFixed(1)}${unit}`,
  };
}

/**
 * Validate a single numeric field against a minimum
 */
function validateMin(
  proposed: number,
  minimum: number,
  reference: string,
  fieldName: string,
  unit: string
): FieldValidation {
  const valid = proposed >= minimum;
  const margin = proposed - minimum;
  return {
    valid,
    required: minimum,
    proposed,
    margin: Math.round(margin * 100) / 100,
    reference,
    message: valid
      ? margin > 0
        ? `+${margin.toFixed(1)}${unit} above min`
        : 'At minimum'
      : `${Math.abs(margin).toFixed(1)}${unit} below min`,
  };
}

export function useCdcComplianceCalculator(
  options: UseCdcComplianceCalculatorOptions = {}
): UseCdcComplianceCalculatorReturn {
  const { initialValues = {} } = options;

  // Merge defaults with initial values
  const defaultForm: CdcComplianceInput = {
    ...CDC_INPUT_DEFAULTS,
    ...initialValues,
    setbacks: {
      ...CDC_INPUT_DEFAULTS.setbacks,
      ...(initialValues.setbacks || {}),
    },
  };

  const [form, setForm] = useState<CdcComplianceInput>(defaultForm);
  const [result, setResult] = useState<CdcComplianceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update a top-level field
  const updateField = useCallback(
    <K extends keyof CdcComplianceInput>(
      field: K,
      value: CdcComplianceInput[K]
    ) => {
      setForm((prev) => ({ ...prev, [field]: value }));
      // Clear previous result when form changes
      setResult(null);
      setError(null);
    },
    []
  );

  // Update a setback field
  const updateSetback = useCallback(
    (field: 'front' | 'sideLeft' | 'sideRight' | 'rear', value: number) => {
      setForm((prev) => ({
        ...prev,
        setbacks: {
          ...prev.setbacks,
          [field]: value,
        },
      }));
      setResult(null);
      setError(null);
    },
    []
  );

  // Calculate real-time validation for all fields
  const validation = useMemo<FormValidation>(() => {
    const { setbacks, hasUpperFloorHabitableRooms } = form;

    // Validate setbacks using existing utility
    const frontCheck = quickValidateSetback('front', setbacks.front);
    const sideLeftCheck = quickValidateSetback('side', setbacks.sideLeft);
    const sideRightCheck = quickValidateSetback('side', setbacks.sideRight);
    const rearCheck = quickValidateSetback('rear', setbacks.rear, hasUpperFloorHabitableRooms);

    // Convert to FieldValidation format
    const front: FieldValidation = {
      valid: frontCheck.compliant,
      required: frontCheck.required,
      proposed: setbacks.front,
      margin: frontCheck.margin,
      reference: CDC_STANDARDS.setbacks.front.reference,
      message: frontCheck.compliant
        ? frontCheck.margin > 0
          ? `+${frontCheck.margin.toFixed(1)}m`
          : 'Meets minimum'
        : `${Math.abs(frontCheck.margin).toFixed(1)}m short`,
    };

    const sideLeft: FieldValidation = {
      valid: sideLeftCheck.compliant,
      required: sideLeftCheck.required,
      proposed: setbacks.sideLeft,
      margin: sideLeftCheck.margin,
      reference: CDC_STANDARDS.setbacks.side.reference,
      message: sideLeftCheck.compliant
        ? sideLeftCheck.margin > 0
          ? `+${sideLeftCheck.margin.toFixed(1)}m`
          : 'Meets minimum'
        : `${Math.abs(sideLeftCheck.margin).toFixed(1)}m short`,
    };

    const sideRight: FieldValidation = {
      valid: sideRightCheck.compliant,
      required: sideRightCheck.required,
      proposed: setbacks.sideRight,
      margin: sideRightCheck.margin,
      reference: CDC_STANDARDS.setbacks.side.reference,
      message: sideRightCheck.compliant
        ? sideRightCheck.margin > 0
          ? `+${sideRightCheck.margin.toFixed(1)}m`
          : 'Meets minimum'
        : `${Math.abs(sideRightCheck.margin).toFixed(1)}m short`,
    };

    const rear: FieldValidation = {
      valid: rearCheck.compliant,
      required: rearCheck.required,
      proposed: setbacks.rear,
      margin: rearCheck.margin,
      reference: CDC_STANDARDS.setbacks.rear.reference,
      message: rearCheck.compliant
        ? rearCheck.margin > 0
          ? `+${rearCheck.margin.toFixed(1)}m`
          : 'Meets minimum'
        : `${Math.abs(rearCheck.margin).toFixed(1)}m short`,
    };

    // Site coverage (max)
    const siteCoverage = validateMax(
      form.siteCoveragePercent,
      CDC_STANDARDS.siteCoverage.maximum,
      CDC_STANDARDS.siteCoverage.reference,
      'Site coverage',
      '%'
    );

    // Landscaped area (min)
    const landscapedArea = validateMin(
      form.landscapedAreaPercent,
      CDC_STANDARDS.landscapedArea.minimum,
      CDC_STANDARDS.landscapedArea.reference,
      'Landscaped area',
      '%'
    );

    // Building height (max)
    const buildingHeight = validateMax(
      form.buildingHeightMeters,
      CDC_STANDARDS.buildingHeight.maximum,
      CDC_STANDARDS.buildingHeight.reference,
      'Building height',
      'm'
    );

    // Storeys (max)
    const storeys = validateMax(
      form.storeys,
      CDC_STANDARDS.storeys.maximum,
      CDC_STANDARDS.storeys.reference,
      'Storeys',
      ''
    );

    // Parking (min based on bedrooms)
    const requiredParking = getRequiredParking(form.bedrooms);
    const parking = validateMin(
      form.parkingSpaces,
      requiredParking,
      CDC_STANDARDS.parking.reference,
      'Parking',
      ' spaces'
    );

    return {
      front,
      sideLeft,
      sideRight,
      rear,
      siteCoverage,
      landscapedArea,
      buildingHeight,
      storeys,
      parking,
    };
  }, [form]);

  // Count passing checks
  const passCount = useMemo(() => {
    return Object.values(validation).filter((v) => v.valid).length;
  }, [validation]);

  const totalChecks = Object.keys(validation).length;
  const isFullyCompliant = passCount === totalChecks;

  // Submit to API
  const submit = useCallback(
    async (address?: string) => {
      setIsLoading(true);
      setError(null);
      setResult(null);

      try {
        const response = await fetch('/api/cdc/compliance-check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...form,
            address,
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `Request failed: ${response.status}`);
        }

        const data = await response.json();
        setResult(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to check compliance';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [form]
  );

  // Reset form
  const reset = useCallback(() => {
    setForm(defaultForm);
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, [defaultForm]);

  return {
    form,
    updateField,
    updateSetback,
    validation,
    passCount,
    totalChecks,
    isFullyCompliant,
    submit,
    result,
    isLoading,
    error,
    reset,
  };
}

export default useCdcComplianceCalculator;

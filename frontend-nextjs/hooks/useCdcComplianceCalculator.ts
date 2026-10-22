/**
 * useCdcComplianceCalculator Hook
 *
 * Form state and live checks for the CDC compliance calculator.
 * Required figures come from the stored Housing Code standards (fetched from
 * /api/cdc/standards and applied with the same parser/selector the API uses).
 * Until they load, or when nothing stored applies, a check is "Not checked".
 *
 * prior-art-checked: rewrite of the existing hook onto lib/cdc; no typed standards remain.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  CdcComplianceInput,
  CdcComplianceResponse,
  CDC_INPUT_DEFAULTS,
  FormValidation,
} from '@/components/cdc/types';
import { parseRows, type ParsedRow, type StandardRow } from '@/lib/cdc/housing-code-standards';
import { evaluateCdcChecks, summariseChecks } from '@/lib/cdc/housing-code-checks';

interface UseCdcComplianceCalculatorOptions {
  /** Initial values for the form */
  initialValues?: Partial<CdcComplianceInput>;
}

interface UseCdcComplianceCalculatorReturn {
  form: CdcComplianceInput;
  updateField: <K extends keyof CdcComplianceInput>(field: K, value: CdcComplianceInput[K]) => void;
  updateSetback: (field: 'front' | 'sideLeft' | 'sideRight' | 'rear', value: number | null) => void;
  /** Live check for every field (pass, fail or not checked). */
  validation: FormValidation;
  passCount: number;
  failCount: number;
  notCheckedCount: number;
  totalChecks: number;
  /** True only when every check was decided and passed. */
  isFullyCompliant: boolean;
  /** Why no stored standards are available, if so. */
  standardsError: string | null;
  submit: (address?: string) => Promise<void>;
  result: CdcComplianceResponse | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
}

export function useCdcComplianceCalculator(
  options: UseCdcComplianceCalculatorOptions = {}
): UseCdcComplianceCalculatorReturn {
  const { initialValues = {} } = options;

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
  const [parsed, setParsed] = useState<ParsedRow[]>([]);
  const [standardsError, setStandardsError] = useState<string | null>('stored standards are loading');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch('/api/cdc/standards');
        const data = (await response.json()) as { rows?: StandardRow[]; error?: string | null };
        if (cancelled) return;
        if (!response.ok || !Array.isArray(data.rows) || data.error) {
          setStandardsError(data.error || `stored standards unavailable (${response.status})`);
          setParsed([]);
          return;
        }
        setParsed(parseRows(data.rows));
        setStandardsError(null);
      } catch (err) {
        if (cancelled) return;
        setStandardsError(`stored standards unavailable: ${err instanceof Error ? err.message : 'unknown error'}`);
        setParsed([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const updateField = useCallback(
    <K extends keyof CdcComplianceInput>(field: K, value: CdcComplianceInput[K]) => {
      setForm((prev) => ({ ...prev, [field]: value }));
      setResult(null);
      setError(null);
    },
    []
  );

  const updateSetback = useCallback(
    (field: 'front' | 'sideLeft' | 'sideRight' | 'rear', value: number | null) => {
      setForm((prev) => ({ ...prev, setbacks: { ...prev.setbacks, [field]: value } }));
      setResult(null);
      setError(null);
    },
    []
  );

  const checks = useMemo(
    () => evaluateCdcChecks(form, parsed, standardsError),
    [form, parsed, standardsError]
  );
  const validation = useMemo(
    () => Object.fromEntries(checks.map((c) => [c.key, c])) as FormValidation,
    [checks]
  );
  const summary = useMemo(() => summariseChecks(checks), [checks]);

  const submit = useCallback(
    async (address?: string) => {
      setIsLoading(true);
      setError(null);
      setResult(null);
      try {
        const response = await fetch('/api/cdc/compliance-check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...form, address }),
        });
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `Request failed: ${response.status}`);
        }
        setResult(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to check compliance');
      } finally {
        setIsLoading(false);
      }
    },
    [form]
  );

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
    passCount: summary.pass,
    failCount: summary.fail,
    notCheckedCount: summary.notChecked,
    totalChecks: summary.total,
    isFullyCompliant: summary.allPass,
    standardsError,
    submit,
    result,
    isLoading,
    error,
    reset,
  };
}

export default useCdcComplianceCalculator;

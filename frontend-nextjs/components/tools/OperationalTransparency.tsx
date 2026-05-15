'use client';

import { useEffect, useRef, useState } from 'react';

export interface TransparencyStep {
  label: string;
  /** Delay in ms before this step appears (from component mount). First step should be 0. */
  ms: number;
}

interface OperationalTransparencyProps {
  steps: TransparencyStep[];
  /** Whether the loading is active. Resets step index when toggled off. */
  active: boolean;
  /** Optional address to display in the header */
  address?: string;
  /** Optional footer note (e.g. "Usually takes 5-10 seconds") */
  note?: string;
}

/**
 * Displays timed sequential loading messages to create operational transparency
 * (labor illusion). Shows users what the system is doing while they wait.
 *
 * Based on the PreDAHistoryTool pipeline progress pattern.
 */
export function OperationalTransparency({ steps, active, address, note }: OperationalTransparencyProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (active && steps.length > 0) {
      setCurrentStep(0);
      // Schedule each step after the first
      timersRef.current = steps.slice(1).map((s, i) =>
        setTimeout(() => setCurrentStep(i + 1), s.ms)
      );
    } else {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
      setCurrentStep(0);
    }
    return () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, [active, steps]);

  if (!active || steps.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 md:p-8">
      {address && (
        <p className="text-sm font-medium text-gray-700 mb-4">Analysing {address}…</p>
      )}
      <div className="space-y-2.5">
        {steps.map((step, i) => (
          <div
            key={i}
            className={`flex items-center gap-3 transition-opacity duration-300 ${
              i <= currentStep ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {i < currentStep ? (
              <div className="w-4 h-4 rounded-full bg-teal-600 flex-shrink-0 flex items-center justify-center">
                <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            ) : i === currentStep ? (
              <div className="w-4 h-4 rounded-full border-2 border-teal-600 border-t-transparent animate-spin flex-shrink-0" />
            ) : (
              <div className="w-4 h-4 rounded-full bg-gray-200 flex-shrink-0" />
            )}
            <span className={`text-xs ${i <= currentStep ? 'text-gray-700' : 'text-gray-400'}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
      {note && (
        <p className="mt-4 text-xs text-gray-400">{note}</p>
      )}
    </div>
  );
}

'use client';

import { useState } from 'react';
import { Ruler } from 'lucide-react';

export interface NumericCheckValues {
  height: string;
  frontSetback: string;
  sideSetback: string;
  gfa: string;
  siteCoverage: string;
  carSpaces: string;
}

interface NumericCheckerProps {
  onValuesChange: (values: NumericCheckValues) => void;
}

const FIELDS: Array<{ key: keyof NumericCheckValues; label: string; unit: string; placeholder: string }> = [
  { key: 'height', label: 'Building height', unit: 'm', placeholder: '0.0' },
  { key: 'gfa', label: 'Gross floor area (GFA)', unit: 'm²', placeholder: '0' },
  { key: 'siteCoverage', label: 'Site coverage', unit: '%', placeholder: '0' },
  { key: 'carSpaces', label: 'Car spaces', unit: '', placeholder: '0' },
];

export function NumericChecker({ onValuesChange }: NumericCheckerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [values, setValues] = useState<NumericCheckValues>({
    height: '',
    frontSetback: '',
    sideSetback: '',
    gfa: '',
    siteCoverage: '',
    carSpaces: '',
  });

  const handleChange = (key: keyof NumericCheckValues, value: string) => {
    const updated = { ...values, [key]: value };
    setValues(updated);
    onValuesChange(updated);
  };

  return (
    <div className="mb-4 border border-teal-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-teal-50 hover:bg-teal-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-teal-600" />
          <span className="text-sm font-medium text-teal-800">Check Fixed-Number Limits</span>
          <span className="text-xs text-teal-500 ml-1">height · GFA · coverage · parking</span>
        </div>
        <span className="text-teal-600 text-xs">{isOpen ? '▲ Hide' : '▼ Show'}</span>
      </button>

      {isOpen && (
        <div className="px-4 py-3 bg-white">
          <p className="text-xs text-gray-500 mb-3">
            Flags provisions with hard numeric limits —
            <span className="text-green-700 font-medium"> complies</span>,
            <span className="text-amber-700 font-medium"> borderline</span>, or
            <span className="text-red-700 font-medium"> fails</span>.
            Contextual controls (setbacks, character, heritage) require professional judgment and are not checked here.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {FIELDS.map(({ key, label, unit, placeholder }) => (
              <div key={key}>
                <label className="block text-xs text-gray-600 mb-1">
                  {label} {unit && <span className="text-gray-400">({unit})</span>}
                </label>
                <input
                  type="number"
                  value={values[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                  placeholder={placeholder}
                  min="0"
                  step="0.1"
                  className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-400"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

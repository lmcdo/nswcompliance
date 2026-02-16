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
  { key: 'height', label: 'Height', unit: 'm', placeholder: '0.0' },
  { key: 'frontSetback', label: 'Front setback', unit: 'm', placeholder: '0.0' },
  { key: 'sideSetback', label: 'Side setback', unit: 'm', placeholder: '0.0' },
  { key: 'gfa', label: 'GFA', unit: 'm²', placeholder: '0' },
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
          <span className="text-sm font-medium text-teal-800">Numeric Compliance Check</span>
          <span className="text-xs text-teal-600">Enter proposed values to check against limits</span>
        </div>
        <span className="text-teal-600 text-xs">{isOpen ? '▲ Hide' : '▼ Show'}</span>
      </button>

      {isOpen && (
        <div className="px-4 py-3 bg-white">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
          <p className="text-xs text-gray-400 mt-2">
            Provisions with numeric limits will be highlighted green (pass), amber (borderline), or red (fail).
          </p>
        </div>
      )}
    </div>
  );
}

'use client';

interface QuickActionChipsProps {
  hasProperty: boolean;
  onSelect: (question: string) => void;
}

// ============================================================
// CURATED CHIPS - Most common homeowner questions (~25 total)
// ============================================================

// Property-specific lookups (require address) - 12 chips
const PROPERTY_LEP = [
  { label: 'Height limit', question: 'What is the height limit?' },
  { label: 'FSR', question: 'What is the FSR?' },
  { label: 'Constraints', question: 'What constraints or overlays apply?' },
];

const PROPERTY_PERMISSIBILITY = [
  { label: 'Dual occupancy', question: 'Is dual occupancy permitted?' },
  { label: 'Granny flat', question: 'Can I build a granny flat?' },
  { label: 'Townhouses', question: 'Are townhouses permitted?' },
];

const PROPERTY_SEPP = [
  { label: 'Housing SEPP', question: 'What am I eligible for under Housing SEPP?' },
];

// DCP provisions removed - provision extraction unreliable, users should check DCP tab
// const PROPERTY_DCP = [];

// General resources (no address needed) - 13 chips
const GUIDES = [
  { label: 'Granny flat guide', question: 'How do I build a granny flat?' },
  { label: 'Second storey guide', question: 'How do I add a second storey?' },
  { label: 'Duplex guide', question: 'How do I build a duplex?' },
];

const PROCESS = [
  { label: 'CDC vs DA?', question: 'Should I use CDC or DA?' },
  { label: 'CDC documents', question: 'What documents do I need for a CDC?' },
  { label: 'DA documents', question: 'What documents do I need for a DA?' },
];

const DEFINITIONS = [
  { label: 'What is FSR?', question: 'What does FSR mean?' },
  { label: 'What is a setback?', question: 'What is a setback?' },
  { label: 'What is BASIX?', question: 'What is BASIX?' },
  { label: 'What is a CDC?', question: 'What is a CDC?' },
  { label: 'What is a DA?', question: 'What is a DA?' },
  { label: 'What is dual occupancy?', question: 'What is dual occupancy?' },
  { label: 'What is Clause 4.6?', question: 'What is a Clause 4.6 variation?' },
];

// ============================================================
// ORGANIZED DISPLAY
// ============================================================

const ADDRESS_LOOKUPS = [
  { category: 'LEP Controls', options: PROPERTY_LEP },
  { category: 'What Can I Build?', options: PROPERTY_PERMISSIBILITY },
  { category: 'SEPP Housing', options: PROPERTY_SEPP },
  // DCP Requirements removed - check DCP tab for detailed provisions
];

const GENERAL_RESOURCES = [
  { category: 'Step-by-Step Guides', options: GUIDES },
  { category: 'Process & Documents', options: PROCESS },
  { category: 'Common Questions', options: DEFINITIONS },
];

export function QuickActionChips({ hasProperty, onSelect }: QuickActionChipsProps) {
  return (
    <div className="space-y-4">
      {/* Property-specific lookups - only show if address selected */}
      {hasProperty && (
        <div className="space-y-2">
          <div className="bg-blue-50 border border-blue-200 rounded px-2 py-1">
            <p className="text-xs font-bold text-blue-800">📍 FOR THIS ADDRESS:</p>
          </div>
          {ADDRESS_LOOKUPS.map(({ category, options }) => (
            <div key={category}>
              <p className="text-xs font-medium text-blue-700 mb-1">{category}</p>
              <div className="flex flex-wrap gap-1">
                {options.map(({ label, question }) => (
                  <button
                    key={label}
                    onClick={() => onSelect(question)}
                    className="px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 text-blue-800 rounded border border-blue-300 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* General resources - always show */}
      <div className="space-y-2">
        <div className="bg-gray-100 border border-gray-300 rounded px-2 py-1">
          <p className="text-xs font-bold text-gray-700">📚 GENERAL RESOURCES:</p>
        </div>
        {GENERAL_RESOURCES.map(({ category, options }) => (
          <div key={category}>
            <p className="text-xs font-medium text-gray-600 mb-1">{category}</p>
            <div className="flex flex-wrap gap-1">
              {options.map(({ label, question }) => (
                <button
                  key={label}
                  onClick={() => onSelect(question)}
                  className="px-2 py-1 text-xs bg-white hover:bg-gray-50 text-gray-700 rounded border border-gray-300 transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

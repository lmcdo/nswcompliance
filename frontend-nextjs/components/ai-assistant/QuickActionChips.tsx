'use client';

interface QuickActionChipsProps {
  hasProperty: boolean;
  onSelect: (question: string) => void;
}

// ============================================================
// ALL DATABASE CONTENT - organized by type
// ============================================================

// 5 GUIDES (step-by-step processes)
const GUIDES = [
  { label: 'Granny flat', question: 'How do I build a granny flat?' },
  { label: 'Second storey', question: 'How do I add a second storey?' },
  { label: 'Duplex', question: 'How do I build a duplex?' },
  { label: 'Knock down rebuild', question: 'How do I knock down and rebuild?' },
  { label: 'Subdivision', question: 'How do I subdivide my property?' },
];

// 12 CHECKLISTS (documents needed)
const CHECKLISTS = [
  { label: 'CDC residential', question: 'What documents do I need for a CDC residential application?' },
  { label: 'DA residential', question: 'What documents do I need for a DA residential application?' },
  { label: 'CDC granny flat', question: 'What documents do I need for a granny flat CDC?' },
  { label: 'CDC dual occupancy', question: 'What documents do I need for a dual occupancy CDC?' },
  { label: 'CDC two-storey addition', question: 'What documents do I need for a two storey addition CDC?' },
  { label: 'CDC swimming pool', question: 'What documents do I need for a swimming pool CDC?' },
  { label: 'CDC garage/carport', question: 'What documents do I need for a garage or carport CDC?' },
  { label: 'CDC deck/pergola', question: 'What documents do I need for a deck or pergola CDC?' },
  { label: 'DA commercial fitout', question: 'What documents do I need for a commercial fitout DA?' },
  { label: 'DA heritage', question: 'What documents do I need for a heritage DA?' },
  { label: 'DA flood zone', question: 'What documents do I need for a flood zone DA?' },
  { label: 'DA bushfire', question: 'What documents do I need for a bushfire prone land DA?' },
];

// 46 Q&As grouped by category
const QA_PATHWAYS = [
  { label: 'CDC vs DA?', question: 'Should I use CDC or DA?' },
  { label: 'CDC process', question: 'What is the CDC process?' },
  { label: 'DA process', question: 'What is the DA process?' },
  { label: 'Site excluded from CDC?', question: 'Is my site excluded from CDC?' },
];

const QA_TIMELINES = [
  { label: 'CDC timeline', question: 'How long does CDC take?' },
  { label: 'DA timeline', question: 'How long does DA take?' },
];

const QA_PROFESSIONALS = [
  { label: 'Need an architect?', question: 'Do I need an architect?' },
  { label: 'Need a certifier?', question: 'Do I need a private certifier?' },
  { label: 'Need a planner?', question: 'Do I need a town planner?' },
];

const QA_CONSTRUCTION = [
  { label: 'What is a Principal Certifier?', question: 'What is a Principal Certifier?' },
  { label: 'What inspections needed?', question: 'What inspections are required during construction?' },
  { label: 'Occupation Certificate', question: 'What is an Occupation Certificate?' },
];

const QA_MODIFICATIONS = [
  { label: 'What is Clause 4.6?', question: 'What is a Clause 4.6 variation?' },
  { label: 'Modify after approval?', question: 'Can I modify my approval after its granted?' },
  { label: 'Section 4.55 modification', question: 'What is a Section 4.55 modification?' },
];

const QA_MISTAKES = [
  { label: 'Common DA rejections', question: 'What are the most common reasons DAs get rejected?' },
  { label: 'What causes delays?', question: 'What causes delays in DA assessment?' },
];

// DEFINITIONS (465 terms - show common ones)
const DEFINITIONS = [
  { label: 'FSR', question: 'What does FSR mean?' },
  { label: 'Setback', question: 'What is a setback?' },
  { label: 'Site coverage', question: 'What is site coverage?' },
  { label: 'GFA', question: 'What is gross floor area?' },
  { label: 'CDC', question: 'What is a CDC?' },
  { label: 'DA', question: 'What is a DA?' },
  { label: 'BASIX', question: 'What is BASIX?' },
  { label: 'LEP', question: 'What is an LEP?' },
  { label: 'DCP', question: 'What is a DCP?' },
  { label: 'Dual occupancy', question: 'What is dual occupancy?' },
  { label: 'Secondary dwelling', question: 'What is a secondary dwelling?' },
  { label: 'Habitable room', question: 'What is a habitable room?' },
];

// PROPERTY-SPECIFIC - complete lists of all available lookups

// LEP controls (from Planning Portal spatial layers)
const PROPERTY_LEP = [
  { label: 'Height limit', question: 'What is the height limit?' },
  { label: 'FSR', question: 'What is the FSR?' },
  { label: 'Constraints/overlays', question: 'What constraints or overlays apply to this property?' },
];

// Permissibility checks (LEP land use table)
const PROPERTY_PERMISSIBILITY = [
  { label: 'Dual occupancy', question: 'Is dual occupancy permitted?' },
  { label: 'Granny flat', question: 'Can I build a granny flat?' },
  { label: 'Townhouses', question: 'Are townhouses permitted?' },
  { label: 'Apartments', question: 'Are apartments permitted?' },
  { label: 'Shop/retail', question: 'Is retail permitted?' },
  { label: 'Home business', question: 'Is a home business permitted?' },
];

// SEPP eligibility
const PROPERTY_SEPP = [
  { label: 'Housing SEPP eligibility', question: 'What am I eligible for under the Housing SEPP?' },
];

// DCP requirements - ALL available topics
const PROPERTY_DCP = [
  // Building controls
  { label: 'Setbacks', question: 'What are the setback requirements?' },
  { label: 'Building form', question: 'What are the building form requirements?' },
  { label: 'Building design', question: 'What are the building design requirements?' },
  { label: 'Site coverage', question: 'What are the site coverage requirements?' },
  // Parking & access
  { label: 'Parking', question: 'What are the parking requirements?' },
  { label: 'Bicycle parking', question: 'What are the bicycle parking requirements?' },
  { label: 'Access', question: 'What are the access requirements?' },
  // Landscaping & environment
  { label: 'Landscaping', question: 'What are the landscaping requirements?' },
  { label: 'Open space', question: 'What are the open space requirements?' },
  { label: 'Tree management', question: 'What are the tree management requirements?' },
  { label: 'Biodiversity', question: 'What are the biodiversity requirements?' },
  // Infrastructure
  { label: 'Stormwater', question: 'What are the stormwater requirements?' },
  { label: 'Waste', question: 'What are the waste requirements?' },
  { label: 'Water', question: 'What are the water requirements?' },
  { label: 'Energy', question: 'What are the energy requirements?' },
  // Amenity
  { label: 'Privacy', question: 'What are the privacy requirements?' },
  { label: 'Fencing', question: 'What are the fencing requirements?' },
  { label: 'Signage', question: 'What are the signage requirements?' },
  { label: 'Safety/CPTED', question: 'What are the safety requirements?' },
  // Other
  { label: 'Streetscape', question: 'What are the streetscape requirements?' },
  { label: 'Subdivision', question: 'What are the subdivision requirements?' },
  { label: 'Social impact', question: 'What are the social impact requirements?' },
  { label: 'Contamination', question: 'What are the contamination requirements?' },
  { label: 'Sustainability', question: 'What are the sustainability requirements?' },
];

// ============================================================
// ORGANIZED DISPLAY
// ============================================================

// Property-specific lookups (require address)
const ADDRESS_LOOKUPS = [
  { category: 'LEP controls', options: PROPERTY_LEP },
  { category: 'What can I build?', options: PROPERTY_PERMISSIBILITY },
  { category: 'SEPP Housing', options: PROPERTY_SEPP },
  { category: 'DCP requirements', options: PROPERTY_DCP },
];

// General resources (no address needed)
const GENERAL_RESOURCES = [
  { category: 'Step-by-step guides', options: GUIDES },
  { category: 'Document checklists', options: CHECKLISTS },
  { category: 'Pathways & process', options: QA_PATHWAYS },
  { category: 'Timelines', options: QA_TIMELINES },
  { category: 'Professionals', options: QA_PROFESSIONALS },
  { category: 'Construction', options: QA_CONSTRUCTION },
  { category: 'Modifications & variations', options: QA_MODIFICATIONS },
  { category: 'Common mistakes', options: QA_MISTAKES },
  { category: 'Planning definitions', options: DEFINITIONS },
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

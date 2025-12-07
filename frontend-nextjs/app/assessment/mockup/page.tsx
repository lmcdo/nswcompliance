'use client';

/**
 * MOCKUP: Provision Type UX Enhancement
 *
 * Demonstrates proposed changes:
 * - Type counts in topic header
 * - Filter dropdown (All / Controls / Controls + Objectives)
 * - Visual grouping by provision type
 * - Density-based defaults
 */

import React, { useState, useEffect, useMemo } from 'react';
import { ChevronDown, ChevronRight, FileText, Filter, Eye, EyeOff } from 'lucide-react';

// Mock data representing real provision structure
const MOCK_DATA = {
  topic: 'Building Form',
  total: 426,
  provisions: {
    controls: [
      { id: 1, marker: 'C12', text: 'Front setback minimum 6m from the primary street frontage, or consistent with established building line where prevailing pattern exists.', page: 45 },
      { id: 2, marker: 'C13', text: 'Side setback minimum 900mm for buildings up to 2 storeys. Increased setbacks required for buildings over 8.5m in height.', page: 45 },
      { id: 3, marker: 'C14', text: 'Rear setback minimum 3m for habitable rooms, 900mm for non-habitable structures.', page: 46 },
      { id: 4, marker: 'C15', text: 'Maximum site coverage 60% for lots under 450m², 55% for lots 450-900m², 50% for lots over 900m².', page: 46 },
      { id: 5, marker: 'C16', text: 'Building height must not exceed 8.5m or 2 storeys, whichever is lesser.', page: 47 },
      { id: 6, marker: 'C17', text: 'Floor space ratio must not exceed 0.5:1 unless specified otherwise in LEP.', page: 47 },
      { id: 7, marker: 'C18', text: 'Minimum 30% of site area must be landscaped with deep soil planting zones.', page: 48 },
      { id: 8, marker: 'C19', text: 'Garages and carports must not project forward of the main building facade.', page: 48 },
    ],
    objectives: [
      { id: 101, marker: 'O1', text: 'Ensure development respects the established streetscape character and maintains visual continuity with adjoining properties.', page: 44 },
      { id: 102, marker: 'O2', text: 'Provide adequate separation between buildings to maintain privacy, solar access, and natural ventilation.', page: 44 },
      { id: 103, marker: 'O3', text: 'Encourage articulated building forms that reduce visual bulk and add architectural interest.', page: 44 },
    ],
    context: [
      { id: 201, text: 'The Summer Hill area has evolved with a distinct residential character dating from the late Victorian and Federation periods. The predominant building stock consists of single and two-storey detached dwellings on regular lot patterns.', page: 42 },
      { id: 202, text: 'Development in this area should respond positively to the established pattern of front gardens, consistent setbacks, and traditional roof forms that contribute to the valued streetscape character.', page: 42 },
      { id: 203, text: 'The topography of the area, with its gentle slopes toward the Cooks River, has influenced the siting and orientation of buildings, with many properties taking advantage of district views.', page: 43 },
      { id: 204, text: 'Street trees, predominantly mature Brush Box and Jacarandas, form an important part of the neighbourhood character and should be protected and complemented by new development.', page: 43 },
      { id: 205, text: 'Many properties in this precinct retain original front fences, garden layouts, and landscape elements that contribute to heritage significance and should be conserved where possible.', page: 43 },
    ]
  }
};

type FilterMode = 'all' | 'controls' | 'controls_objectives';

export default function MockupPage() {
  const [filterMode, setFilterMode] = useState<FilterMode>('controls');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['controls']));
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const counts = {
    controls: MOCK_DATA.provisions.controls.length,
    objectives: MOCK_DATA.provisions.objectives.length,
    context: MOCK_DATA.provisions.context.length,
  };

  const filterLabels: Record<FilterMode, string> = {
    all: 'All provisions',
    controls: 'Controls only',
    controls_objectives: 'Controls + Objectives',
  };

  const visibleSections = useMemo(() => {
    switch (filterMode) {
      case 'controls':
        return ['controls'];
      case 'controls_objectives':
        return ['controls', 'objectives'];
      case 'all':
      default:
        return ['controls', 'objectives', 'context'];
    }
  }, [filterMode]);

  // Auto-expand visible sections
  useEffect(() => {
    setExpandedSections(new Set(visibleSections));
  }, [visibleSections]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-teal-700 text-white px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 text-teal-200 text-sm mb-1">
            <span>MOCKUP</span>
            <span>•</span>
            <span>Proposed UX Enhancement</span>
          </div>
          <h1 className="text-2xl font-semibold">Provision Type Display</h1>
          <p className="text-teal-100 mt-1">Demonstrating visual hierarchy and filtering for professional workflows</p>
        </div>
      </header>

      {/* Mockup explanation */}
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-3">
        <div className="max-w-4xl mx-auto text-sm text-amber-800">
          <strong>What's new:</strong> Type counts in header • Filter by provision type • Visual grouping • Collapsible sections
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Topic Card - Enhanced */}
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          {/* Topic Header - NEW DESIGN */}
          <div className="bg-gray-50 border-b px-5 py-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{MOCK_DATA.topic}</h2>
                <div className="flex items-center gap-3 mt-2 text-sm">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 font-medium">
                    {counts.controls} controls
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                    {counts.objectives} objectives
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-gray-200 text-gray-600 font-medium">
                    {counts.context} context
                  </span>
                </div>
              </div>

              {/* Filter Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Filter className="h-4 w-4" />
                  {filterLabels[filterMode]}
                  <ChevronDown className="h-4 w-4" />
                </button>

                {showFilterDropdown && (
                  <div className="absolute right-0 mt-1 w-56 bg-white border rounded-lg shadow-lg z-10">
                    {(Object.keys(filterLabels) as FilterMode[]).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => {
                          setFilterMode(mode);
                          setShowFilterDropdown(false);
                        }}
                        className={`w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                          filterMode === mode ? 'bg-teal-50 text-teal-700 font-medium' : 'text-gray-700'
                        }`}
                      >
                        {filterLabels[mode]}
                        {mode === 'controls' && (
                          <span className="block text-xs text-gray-500 mt-0.5">Best for CDC assessment</span>
                        )}
                        {mode === 'controls_objectives' && (
                          <span className="block text-xs text-gray-500 mt-0.5">Recommended for DA</span>
                        )}
                        {mode === 'all' && (
                          <span className="block text-xs text-gray-500 mt-0.5">Full context view</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Filter indicator */}
            {filterMode !== 'all' && (
              <div className="mt-3 text-xs text-gray-500 flex items-center gap-1">
                <Eye className="h-3 w-3" />
                Showing {filterMode === 'controls' ? counts.controls : counts.controls + counts.objectives} of {MOCK_DATA.total} provisions
                <button
                  onClick={() => setFilterMode('all')}
                  className="text-teal-600 hover:text-teal-700 ml-1 underline"
                >
                  Show all
                </button>
              </div>
            )}
          </div>

          {/* Provisions List */}
          <div className="divide-y">
            {/* CONTROLS SECTION */}
            {visibleSections.includes('controls') && (
              <div>
                <button
                  onClick={() => toggleSection('controls')}
                  className="w-full flex items-center gap-2 px-5 py-3 bg-teal-50 hover:bg-teal-100 transition-colors text-left"
                >
                  {expandedSections.has('controls') ? (
                    <ChevronDown className="h-4 w-4 text-teal-600" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-teal-600" />
                  )}
                  <span className="font-semibold text-teal-800">Controls</span>
                  <span className="text-teal-600 text-sm">({counts.controls})</span>
                </button>

                {expandedSections.has('controls') && (
                  <div className="divide-y divide-gray-100">
                    {MOCK_DATA.provisions.controls.map((prov) => (
                      <div key={prov.id} className="px-5 py-3 hover:bg-gray-50">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-bold bg-teal-600 text-white min-w-[40px]">
                            {prov.marker}
                          </span>
                          <div className="flex-1">
                            <p className="text-gray-800 text-sm leading-relaxed">{prov.text}</p>
                          </div>
                          <button className="text-xs text-gray-400 hover:text-teal-600 whitespace-nowrap">
                            pg {prov.page}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* OBJECTIVES SECTION */}
            {visibleSections.includes('objectives') && (
              <div>
                <button
                  onClick={() => toggleSection('objectives')}
                  className="w-full flex items-center gap-2 px-5 py-3 bg-blue-50 hover:bg-blue-100 transition-colors text-left"
                >
                  {expandedSections.has('objectives') ? (
                    <ChevronDown className="h-4 w-4 text-blue-600" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-blue-600" />
                  )}
                  <span className="font-semibold text-blue-800">Objectives</span>
                  <span className="text-blue-600 text-sm">({counts.objectives})</span>
                </button>

                {expandedSections.has('objectives') && (
                  <div className="divide-y divide-gray-100">
                    {MOCK_DATA.provisions.objectives.map((prov) => (
                      <div key={prov.id} className="px-5 py-3 hover:bg-gray-50">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-bold bg-blue-600 text-white min-w-[40px]">
                            {prov.marker}
                          </span>
                          <div className="flex-1">
                            <p className="text-gray-800 text-sm leading-relaxed">{prov.text}</p>
                          </div>
                          <button className="text-xs text-gray-400 hover:text-teal-600 whitespace-nowrap">
                            pg {prov.page}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* CONTEXT SECTION */}
            {visibleSections.includes('context') && (
              <div>
                <button
                  onClick={() => toggleSection('context')}
                  className="w-full flex items-center gap-2 px-5 py-3 bg-gray-100 hover:bg-gray-200 transition-colors text-left"
                >
                  {expandedSections.has('context') ? (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-500" />
                  )}
                  <span className="font-semibold text-gray-600">Character & Context</span>
                  <span className="text-gray-500 text-sm">({counts.context})</span>
                </button>

                {expandedSections.has('context') && (
                  <div className="divide-y divide-gray-100 bg-gray-50">
                    {MOCK_DATA.provisions.context.map((prov) => (
                      <div key={prov.id} className="px-5 py-3">
                        <div className="flex items-start gap-3">
                          <div className="w-[40px]" /> {/* Spacer for alignment */}
                          <div className="flex-1">
                            <p className="text-gray-600 text-sm leading-relaxed italic">{prov.text}</p>
                          </div>
                          <button className="text-xs text-gray-400 hover:text-teal-600 whitespace-nowrap">
                            pg {prov.page}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Explanation Cards */}
        <div className="grid md:grid-cols-2 gap-6 mt-8">
          <div className="bg-white rounded-lg border p-5">
            <h3 className="font-semibold text-gray-900 mb-3">For CDC Certifiers</h3>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-teal-600">✓</span>
                Default to "Controls only" view
              </li>
              <li className="flex items-start gap-2">
                <span className="text-teal-600">✓</span>
                Numeric requirements prominent
              </li>
              <li className="flex items-start gap-2">
                <span className="text-teal-600">✓</span>
                Quick page reference for verification
              </li>
            </ul>
          </div>

          <div className="bg-white rounded-lg border p-5">
            <h3 className="font-semibold text-gray-900 mb-3">For DA Planners</h3>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-600">✓</span>
                Access to objectives for merit arguments
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600">✓</span>
                Character context for design decisions
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600">✓</span>
                Full provision set available
              </li>
            </ul>
          </div>
        </div>

        {/* Current vs Proposed */}
        <div className="mt-8 bg-white rounded-lg border overflow-hidden">
          <div className="bg-gray-100 px-5 py-3 border-b">
            <h3 className="font-semibold text-gray-900">Before vs After</h3>
          </div>
          <div className="grid md:grid-cols-2 divide-x">
            <div className="p-5">
              <h4 className="text-sm font-medium text-red-600 mb-3">❌ Current</h4>
              <ul className="text-sm text-gray-600 space-y-2">
                <li>• All 426 provisions in flat list</li>
                <li>• No visual type distinction</li>
                <li>• Controls mixed with context</li>
                <li>• User must read everything</li>
              </ul>
            </div>
            <div className="p-5">
              <h4 className="text-sm font-medium text-green-600 mb-3">✓ Proposed</h4>
              <ul className="text-sm text-gray-600 space-y-2">
                <li>• Type counts visible upfront</li>
                <li>• Filter by workflow need</li>
                <li>• Visual hierarchy guides reading</li>
                <li>• Context available but not noisy</li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t px-6 py-4 mt-8">
        <div className="max-w-4xl mx-auto text-center text-sm text-gray-500">
          This is a UX mockup demonstrating proposed changes. Not connected to live data.
        </div>
      </footer>
    </div>
  );
}

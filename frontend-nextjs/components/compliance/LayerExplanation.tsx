/**
 * Layer Explanation Component — Scope Hierarchy
 *
 * Shows how the 606 property-specific provisions break down by their source (layer).
 * Each layer represents a different applicability rule.
 *
 * Colour map (shared with filter buttons):
 *   generic      → teal   #14b8a6  (bg-teal-500)    — Apply to all properties
 *   use_specific → blue   #3b82f6  (bg-blue-500)    — Apply because of zone
 *   condition    → amber  #f59e0b  (bg-amber-500)   — Apply because of heritage/constraints
 *   precinct     → purple #8b5cf6  (bg-purple-500)  — Apply because of precinct character
 */

import { Info, ChevronDown } from 'lucide-react';
import { useState } from 'react';

// Must mirror COUNCIL_LAYER_LABELS / DEFAULT_LAYER_LABELS in ProvisionsByTocStructure
const LAYER_LABELS: Record<string, Record<string, string>> = {
  ashfield:    { generic: 'Ashfield-wide',    precinct: 'Village Precinct' },
  leichhardt:  { generic: 'Leichhardt-wide',  precinct: 'Distinct Neighbourhood' },
  marrickville:{ generic: 'Marrickville-wide', precinct: 'Precinct Character' },
};

const DEFAULT_LABELS = { generic: 'LGA-wide', precinct: 'Precinct' };

interface LayerExplanationProps {
  zone?: string;
  heritage?: boolean;
  hcaName?: string;
  precinctName?: string;
  formerCouncil?: string;
  layerCounts?: {
    generic: number;
    use_specific: number;
    condition: number;
    precinct: number;
  };
  layerFilter?: string | null;
  onLayerFilterChange?: (layer: string | null) => void;
  // Heritage HCA details
  generalHeritageCount?: number;
  hcaSpecificCount?: number;
  totalHeritageCount?: number;
  // DA mode context
  isDaMode?: boolean;
}

export function LayerExplanation({
  zone,
  heritage,
  hcaName,
  precinctName,
  formerCouncil,
  layerCounts,
  layerFilter,
  onLayerFilterChange,
  generalHeritageCount,
  hcaSpecificCount,
  totalHeritageCount,
  isDaMode,
}: LayerExplanationProps) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  console.log('[LayerExplanation] Received props:', {
    formerCouncil,
    layerCounts,
    layerFilter,
    isDaMode,
    zone,
    heritage,
    precinctName,
  });

  const labels = (formerCouncil && LAYER_LABELS[formerCouncil.toLowerCase()]) || DEFAULT_LABELS;
  const genericLabel = labels.generic;
  const precinctLabel = labels.precinct;

  const totalCount = layerCounts
    ? Object.values(layerCounts).reduce((a, b) => a + b, 0)
    : 0;

  const layers = [
    {
      key: 'generic',
      label: genericLabel,
      description: `Apply to all properties in ${formerCouncil || 'this council'}`,
      color: '#14b8a6',
      count: layerCounts?.generic || 0,
      active: true
    },
    ...(zone ? [{
      key: 'use_specific',
      label: 'Zone-Specific',
      description: `Apply because your property is in ${zone} zone`,
      color: '#3b82f6',
      count: layerCounts?.use_specific || 0,
      active: true
    }] : []),
    ...(heritage ? [{
      key: 'condition',
      label: 'Heritage',
      description: `Apply because your property is ${hcaName ? `in ${hcaName}` : 'heritage listed'}`,
      color: '#f59e0b',
      count: layerCounts?.condition || 0,
      active: true
    }] : []),
    ...(precinctName ? [{
      key: 'precinct',
      label: precinctLabel,
      description: `Apply because your property is in ${precinctName}`,
      color: '#8b5cf6',
      count: layerCounts?.precinct || 0,
      active: true
    }] : []),
  ];

  return (
    <div className="border border-gray-200 rounded-lg p-3 mt-2 bg-white">
      {/* Header: explain the scope cascade */}
      <div className="mb-3 pb-3 border-b border-gray-200">
        <div className="flex items-start gap-2 mb-2">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-gray-600 leading-relaxed">
            <strong className="text-gray-700">{totalCount} provisions apply to this property</strong>
            <span className="text-gray-500"> based on: {zone && `${zone} zone`}{zone && heritage && ', '}{heritage && (hcaName ? hcaName : 'heritage listed')}{(zone || heritage) && precinctName && ', '}{precinctName}.</span>
          </div>
        </div>

        {/* Expandable breakdown */}
        <button
          onClick={() => setShowBreakdown(v => !v)}
          className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-800 font-medium"
        >
          <ChevronDown className={`w-3 h-3 transition-transform ${showBreakdown ? 'rotate-180' : ''}`} />
          {showBreakdown ? 'Hide' : 'Show'} breakdown by source
        </button>
      </div>

      {/* Breakdown: show layer composition */}
      {showBreakdown && (
        <div className="mb-3 pb-3 border-b border-gray-200 space-y-2">
          <div className="text-xs font-semibold text-gray-700 mb-2">These {totalCount} provisions come from:</div>
          {layers.map(layer => (
            <div key={layer.key} className="flex items-center gap-2.5 text-xs">
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: layer.color }}
              />
              <div className="flex-1">
                <span className="text-gray-700">
                  <strong>{layer.count}</strong> {layer.label.toLowerCase()}
                </span>
                <span className="text-gray-500 text-[11px]"> — {layer.description}</span>
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between text-xs mt-2.5 pt-2 border-t border-gray-100">
            <span className="text-gray-600">Total:</span>
            <span className="font-semibold text-gray-800">{totalCount} provisions</span>
          </div>
        </div>
      )}

      {/* Filter buttons — hidden in DA mode (section-first workflow; layer filtering breaks section grouping) */}
      {!isDaMode && <div>
        <div className="text-xs font-semibold text-gray-700 mb-2">
          Filter by source (how provisions apply):
        </div>
        <div className="text-xs text-gray-600 mb-2">
          These {totalCount} provisions come from different sources based on your property's zone, heritage status, and precinct.
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* All layers button */}
          <button
            onClick={() => onLayerFilterChange?.(null)}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
              !layerFilter
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All ({totalCount})
          </button>

          {/* Individual layer buttons */}
          {layers.map(layer => (
            <button
              key={layer.key}
              onClick={() => onLayerFilterChange?.(layerFilter === layer.key ? null : layer.key)}
              disabled={layer.count === 0}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors ${
                layerFilter === layer.key
                  ? 'text-white'
                  : layer.count > 0
                    ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    : 'bg-gray-50 text-gray-400 cursor-not-allowed'
              }`}
              style={layerFilter === layer.key ? { backgroundColor: layer.color } : {}}
              title={layer.description}
            >
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: layer.color }}
              ></span>
              <span>{layer.label} ({layer.count})</span>
            </button>
          ))}
        </div>
      </div>}

      {/* Heritage HCA details - show when heritage layer is selected (non-DA mode only) */}
      {!isDaMode && layerFilter === 'condition' && heritage && totalHeritageCount && totalHeritageCount > 0 && (
        <div className="mt-3 pt-3 border-t border-amber-200">
          <div className="bg-amber-50/50 rounded-md p-3 space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
              <span className="text-xs font-semibold text-amber-900">
                {hcaName || 'Heritage Conservation Area'}
              </span>
            </div>
            <div className="space-y-1.5 text-xs text-amber-800">
              <p>
                <strong>{generalHeritageCount} general heritage provisions</strong> apply to all heritage properties in Inner West
              </p>
              {hcaSpecificCount && hcaSpecificCount > 0 && (
                <p>
                  <strong>{hcaSpecificCount} {hcaName ? hcaName.split(' ')[0] : 'HCA'}-specific provisions</strong> apply only to this HCA
                </p>
              )}
              <p className="text-xs text-amber-600 pt-2 border-t border-amber-200">
                {totalHeritageCount} total heritage provisions for this property
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

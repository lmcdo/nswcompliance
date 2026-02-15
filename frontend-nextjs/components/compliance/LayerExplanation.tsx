/**
 * Layer Explanation Component
 *
 * Explains which layers apply and why. Colours and labels must stay in sync
 * with the "Show from" filter buttons in ProvisionsByTocStructure.
 *
 * Colour map (shared with filter buttons):
 *   generic      → teal   #14b8a6  (bg-teal-500)
 *   use_specific → blue   #3b82f6  (bg-blue-500)
 *   condition    → amber  #f59e0b  (bg-amber-500)
 *   precinct     → purple #8b5cf6  (bg-purple-500)
 */

import { Info } from 'lucide-react';

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
}

export function LayerExplanation({
  zone,
  heritage,
  hcaName,
  precinctName,
  formerCouncil,
  layerCounts,
  layerFilter,
  onLayerFilterChange
}: LayerExplanationProps) {
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
    <div className="border border-gray-200 rounded-lg p-2.5 mt-2">
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
    </div>
  );
}

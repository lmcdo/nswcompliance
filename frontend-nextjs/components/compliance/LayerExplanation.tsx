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
}

export function LayerExplanation({
  zone,
  heritage,
  hcaName,
  precinctName,
  formerCouncil
}: LayerExplanationProps) {
  const labels = (formerCouncil && LAYER_LABELS[formerCouncil.toLowerCase()]) || DEFAULT_LABELS;
  const genericLabel = labels.generic;
  const precinctLabel = labels.precinct;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2">
      <div className="flex items-start gap-2">
        <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="text-xs font-semibold text-blue-900 mb-1.5">
            Why am I seeing these provisions?
          </div>
          <div className="space-y-1 text-xs text-blue-800">

            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-teal-500 rounded-full flex-shrink-0"></span>
              <span><strong>{genericLabel}:</strong> Apply to all properties in {formerCouncil || 'this council'}</span>
            </div>

            {zone && (
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-blue-500 rounded-full flex-shrink-0"></span>
                <span><strong>Zone-Specific:</strong> Apply because your property is in <strong>{zone}</strong> zone</span>
              </div>
            )}

            {heritage && (
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-amber-500 rounded-full flex-shrink-0"></span>
                <span><strong>Heritage:</strong> Apply because your property is {hcaName ? `in ${hcaName}` : 'heritage listed'}</span>
              </div>
            )}

            {precinctName && (
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-purple-500 rounded-full flex-shrink-0"></span>
                <span><strong>{precinctLabel}:</strong> Apply because your property is in <strong>{precinctName}</strong></span>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}

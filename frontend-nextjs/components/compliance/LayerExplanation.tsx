/**
 * Layer Explanation Component
 *
 * Displays always-visible explanation of the 4-layer applicability model
 * Replaces hover tooltips with discoverable, accessible information
 */

import { Info } from 'lucide-react';

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
  const councilName = formerCouncil || 'this council';

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-start gap-2">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-blue-900 mb-2">
            Why am I seeing these provisions?
          </h4>
          <div className="space-y-1.5 text-sm text-blue-800">
            <div className="flex items-start gap-2">
              <span className="inline-block w-2 h-2 bg-purple-500 rounded-full mt-1.5 flex-shrink-0"></span>
              <div>
                <strong>Generic:</strong> Apply to ALL properties in {councilName}
              </div>
            </div>

            {zone && (
              <div className="flex items-start gap-2">
                <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0"></span>
                <div>
                  <strong>Zone-Specific:</strong> Apply because your property is in <strong>{zone}</strong> zone
                </div>
              </div>
            )}

            {heritage && (
              <div className="flex items-start gap-2">
                <span className="inline-block w-2 h-2 bg-amber-500 rounded-full mt-1.5 flex-shrink-0"></span>
                <div>
                  <strong>Heritage:</strong> Apply because your property is {hcaName ? `in ${hcaName}` : 'heritage listed'}
                </div>
              </div>
            )}

            {precinctName && (
              <div className="flex items-start gap-2">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full mt-1.5 flex-shrink-0"></span>
                <div>
                  <strong>Precinct:</strong> Apply because your property is in <strong>{precinctName}</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

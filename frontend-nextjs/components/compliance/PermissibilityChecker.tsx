'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

const DEVELOPMENT_TYPES = [
  { value: 'secondary_dwelling', label: 'Granny Flat / Secondary Dwelling' },
  { value: 'dual_occupancy', label: 'Dual Occupancy' },
  { value: 'dwelling_house', label: 'Dwelling House (Single House)' },
  { value: 'multi_dwelling', label: 'Multi Dwelling Housing (Townhouses)' },
  { value: 'residential_flat', label: 'Residential Flat Building (Apartments)' },
  { value: 'shop_top_housing', label: 'Shop Top Housing' },
  { value: 'commercial', label: 'Commercial / Business Premises' },
  { value: 'office', label: 'Office Premises' },
  { value: 'retail', label: 'Retail Premises' },
  { value: 'child_care', label: 'Child Care Centre' },
  { value: 'boarding_house', label: 'Boarding House' },
  { value: 'mixed_use', label: 'Mixed Use Development' },
  { value: 'community_facility', label: 'Community Facility' }
];

interface PermissibilityCheckerProps {
  propertyAddress: string;
}

interface PermissibilityResult {
  success: boolean;
  permitted: boolean;
  permissibility?: string;
  zone?: string;
  zone_name?: string;
  lga?: string;
  formerCouncil?: string;
  summary?: string;
  reason?: string;
  notes?: string;
  lep_controls?: {
    general?: {
      max_height?: number;
      max_fsr?: number;
    };
    dev_type_specific?: Array<{
      clause_number: string;
      clause_title: string;
      requirements: string[];
      applies_to_zones?: string[];
    }>;
  };
  dcp_sections?: Array<{
    category: string;
    subcategory: string;
    requirement_count: number;
  }>;
  alternative_options?: string[];
  error?: string;
}

export function PermissibilityChecker({ propertyAddress }: PermissibilityCheckerProps) {
  const [selectedDevType, setSelectedDevType] = useState('');
  const [result, setResult] = useState<PermissibilityResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function checkPermissibility() {
    if (!selectedDevType) return;

    setLoading(true);
    try {
      const response = await fetch('/api/permissibility/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: propertyAddress,
          developmentType: selectedDevType
        })
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Permissibility check failed:', error);
      setResult({
        success: false,
        permitted: false,
        error: 'Failed to check permissibility. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-2">Can I Build...?</h2>
      <p className="text-sm text-gray-600 mb-4">
        Check if your development type is permitted in this zone
      </p>

      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-2">
            Select Development Type
          </label>
          <select
            value={selectedDevType}
            onChange={(e) => setSelectedDevType(e.target.value)}
            className="w-full p-2 border rounded-md"
            disabled={loading}
          >
            <option value="">Choose development type...</option>
            {DEVELOPMENT_TYPES.map(dt => (
              <option key={dt.value} value={dt.value}>
                {dt.label}
              </option>
            ))}
          </select>
        </div>

        <Button
          onClick={checkPermissibility}
          disabled={!selectedDevType || loading}
        >
          {loading ? 'Checking...' : 'Check Permissibility'}
        </Button>
      </div>

      {result && (
        <div className={`mt-6 p-4 rounded-lg border-2 ${
          result.permitted
            ? 'bg-green-50 border-green-500'
            : 'bg-red-50 border-red-500'
        }`}>
          <div className="flex items-start gap-3">
            <span className="text-3xl">
              {result.permitted ? '✅' : '❌'}
            </span>

            <div className="flex-1">
              <h3 className={`text-lg font-semibold mb-2 ${
                result.permitted ? 'text-green-900' : 'text-red-900'
              }`}>
                {result.permitted ? 'YES - PERMITTED' : 'NO - PROHIBITED'}
              </h3>

              {result.permitted ? (
                <>
                  <p className="text-sm text-gray-700 mb-3">
                    {result.summary}
                  </p>

                  {result.notes && (
                    <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
                      <p className="text-sm text-blue-900">
                        <strong>Note:</strong> {result.notes}
                      </p>
                    </div>
                  )}

                  {result.lep_controls?.dev_type_specific && result.lep_controls.dev_type_specific.length > 0 && (
                    <div className="mb-3">
                      <h4 className="font-medium text-sm mb-2">LEP Controls:</h4>
                      {result.lep_controls.dev_type_specific.map((clause) => (
                        <div key={clause.clause_number} className="mb-2 p-2 bg-white rounded border">
                          <p className="text-sm font-medium">
                            Clause {clause.clause_number}: {clause.clause_title}
                          </p>
                          {clause.requirements && clause.requirements.length > 0 && (
                            <ul className="text-sm text-gray-600 ml-4 list-disc mt-1">
                              {clause.requirements.map((req: string, i: number) => (
                                <li key={i}>{req}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {result.lep_controls?.general && (
                    <div className="mb-3">
                      <h4 className="font-medium text-sm mb-2">General Controls:</h4>
                      <ul className="text-sm text-gray-600 ml-4 list-disc">
                        {result.lep_controls.general.max_height && (
                          <li>Maximum height: {result.lep_controls.general.max_height}m (Clause 4.3)</li>
                        )}
                        {result.lep_controls.general.max_fsr && (
                          <li>Maximum FSR: {result.lep_controls.general.max_fsr}:1 (Clause 4.4)</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {result.dcp_sections && result.dcp_sections.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">DCP Requirements:</h4>
                      <p className="text-sm text-gray-600">
                        {result.dcp_sections.reduce((sum, s) => sum + s.requirement_count, 0)} requirements
                        across {result.dcp_sections.length} DCP sections apply to this development type
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-red-700 mb-3">
                    {result.reason}
                  </p>

                  {result.error && (
                    <p className="text-sm text-red-600 mb-3">
                      {result.error}
                    </p>
                  )}

                  {result.alternative_options && result.alternative_options.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">
                        Alternative development types permitted in {result.zone} zone:
                      </h4>
                      <ul className="text-sm text-gray-600 ml-4 list-disc">
                        {result.alternative_options.slice(0, 8).map((alt, i) => (
                          <li key={i}>{alt.replace(/_/g, ' ')}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}

              {result.zone && (
                <div className="text-xs text-gray-500 mt-3 pt-3 border-t">
                  Zone: {result.zone_name} ({result.zone}) • {result.lga} • {result.formerCouncil}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

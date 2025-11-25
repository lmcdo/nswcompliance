'use client';

/**
 * Heritage Provisions Sub-Component (DQ-11)
 * Groups Ashfield heritage provisions by type: control, character, descriptive
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface Provision {
  id: number;
  provision_text: string;
  v2_heritage_type?: 'control' | 'character' | 'descriptive';
  v2_heritage_element?: string[];
  v2_heritage_hca?: string;
}

interface HeritageProvisionsProps {
  provisions: Provision[];
}

const HERITAGE_TYPE_LABELS: Record<string, string> = {
  control: 'Actionable Controls',
  character: 'HCA Character Statements',
  descriptive: 'Background Information',
};

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  control: 'bg-green-100 text-green-800 border-green-300',
  character: 'bg-blue-100 text-blue-800 border-blue-300',
  descriptive: 'bg-gray-100 text-gray-600 border-gray-300',
};

const HERITAGE_ELEMENT_LABELS: Record<string, string> = {
  roof: 'Roof',
  verandah: 'Verandah',
  window: 'Windows',
  door: 'Doors',
  fence: 'Fencing',
  garden: 'Gardens',
  facade: 'Facade',
  chimney: 'Chimney',
  infill: 'Infill',
  car_parking: 'Parking',
  demolition: 'Demolition',
  interior: 'Interior',
  materials: 'Materials',
  setback: 'Setbacks',
  scale: 'Scale',
  general: 'General',
};

export function HeritageProvisions({ provisions }: HeritageProvisionsProps) {
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['control']));
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());

  // Group by heritage type
  const byType: Record<string, Provision[]> = { control: [], character: [], descriptive: [] };
  provisions.forEach(p => {
    const type = p.v2_heritage_type || 'descriptive';
    if (!byType[type]) byType[type] = [];
    byType[type].push(p);
  });

  const toggleType = (type: string) => {
    setExpandedTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const toggleProvision = (id: number) => {
    setExpandedProvisions(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const typeOrder = ['control', 'character', 'descriptive'];

  return (
    <div className="space-y-3">
      {typeOrder.map(type => {
        const typeProvisions = byType[type];
        if (!typeProvisions || typeProvisions.length === 0) return null;

        const isExpanded = expandedTypes.has(type);
        const displayLimit = type === 'control' ? 20 : 5;

        return (
          <div key={type} className={`border rounded-lg ${HERITAGE_TYPE_COLORS[type]}`}>
            <div
              className="px-3 py-2 cursor-pointer flex items-center justify-between"
              onClick={() => toggleType(type)}
            >
              <div className="flex items-center gap-2">
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                <span className="font-medium">{HERITAGE_TYPE_LABELS[type]}</span>
                <Badge variant="secondary" className="text-xs">{typeProvisions.length}</Badge>
              </div>
              {type === 'control' && (
                <span className="text-xs opacity-75">Checkable requirements</span>
              )}
            </div>

            {isExpanded && (
              <div className="px-3 pb-3 space-y-2 bg-white rounded-b-lg">
                {typeProvisions.slice(0, displayLimit).map(provision => (
                  <div key={provision.id} className="border rounded p-2 bg-white">
                    <div className="flex items-center gap-1 mb-1 flex-wrap">
                      {provision.v2_heritage_element?.map(elem => (
                        <Badge key={elem} variant="outline" className="text-xs bg-purple-50">
                          {HERITAGE_ELEMENT_LABELS[elem] || elem}
                        </Badge>
                      ))}
                      {provision.v2_heritage_hca && (
                        <Badge variant="outline" className="text-xs bg-amber-50">
                          {provision.v2_heritage_hca.replace(/_/g, ' ')}
                        </Badge>
                      )}
                    </div>
                    <p
                      className={`text-sm cursor-pointer ${expandedProvisions.has(provision.id) ? '' : 'line-clamp-2'}`}
                      onClick={() => toggleProvision(provision.id)}
                    >
                      {provision.provision_text}
                    </p>
                  </div>
                ))}
                {typeProvisions.length > displayLimit && (
                  <p className="text-xs text-gray-500 text-center">
                    Showing {displayLimit} of {typeProvisions.length}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

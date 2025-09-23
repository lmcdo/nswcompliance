'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Building, Home, Users, FileText } from 'lucide-react';
import { DevelopmentTypeSelector } from '@/components/compliance/DevelopmentTypeSelector';
import { ReferencedLegislationAccordion } from '@/components/compliance/ReferencedLegislationAccordion';

interface GroupedSetbackDisplayProps {
 zone: string;
 groupedSetbacks: Record<string, any[]>;
}

const DEV_TYPE_NAMES: Record<string, string> = {
 'dwelling_house': 'Single Dwelling House',
 'dual_occupancy': 'Dual Occupancy',
 'multi_dwelling_housing': 'Multi Dwelling Housing',
 'residential_flat_building': 'Residential Flat Buildings',
 'shop_top_housing': 'Shop Top Housing',
 'general': 'General Requirements'
};

const DEV_TYPE_ICONS: Record<string, any> = {
 'dwelling_house': Home,
 'dual_occupancy': Users,
 'multi_dwelling_housing': Building,
 'residential_flat_building': Building,
 'shop_top_housing': Building,
 'general': FileText
};

export function GroupedSetbackDisplay({ zone, groupedSetbacks }: GroupedSetbackDisplayProps) {
 const [selectedTypes, setSelectedTypes] = useState<string[]>(Object.keys(groupedSetbacks));
 const [expandedTypes, setExpandedTypes] = useState<string[]>(Object.keys(groupedSetbacks));

 const toggleExpanded = (type: string) => {
 setExpandedTypes(prev =>
 prev.includes(type)
 ? prev.filter(t => t !== type)
 : [...prev, type]
 );
 };

 return (
 <div className="space-y-6">
 {/* Development Type Selector */}
 <DevelopmentTypeSelector 
 zone={zone}
 onSelectionChange={setSelectedTypes}
 />

 {/* Grouped Setback Display */}
 <div className="space-y-4">
 {Object.entries(groupedSetbacks)
 .filter(([devType]) => selectedTypes.includes(devType))
 .map(([devType, setbacks]) => {
 const Icon = DEV_TYPE_ICONS[devType] || FileText;
 const isExpanded = expandedTypes.includes(devType);
 
 // Group setbacks by boundary type
 const byBoundary = setbacks.reduce((acc: any, s: any) => {
 if (!acc[s.boundary_type]) acc[s.boundary_type] = [];
 acc[s.boundary_type].push(s);
 return acc;
 }, {});

 return (
 <div key={devType} className="border border-gray-200 rounded-lg overflow-hidden">
 <button
 onClick={() => toggleExpanded(devType)}
 className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
 >
 <div className="flex items-center gap-3">
 <Icon className="h-5 w-5 text-gray-600" />
 <h3 className="font-semibold text-gray-900">
 {DEV_TYPE_NAMES[devType] || devType}
 </h3>
 <span className="text-sm text-gray-500">
 ({setbacks.length} provisions)
 </span>
 </div>
 {isExpanded ? <ChevronUp /> : <ChevronDown />}
 </button>

 {isExpanded && (
 <div className="p-4 space-y-3">
 {/* Summary of setbacks */}
 <div className="grid grid-cols-3 gap-4 mb-4">
 {['front', 'side', 'rear'].map(boundary => {
 const boundarySetbacks = byBoundary[boundary] || [];
 const values = boundarySetbacks.map((s: any) => s.value);
 const min = Math.min(...values);
 const max = Math.max(...values);
 
 return (
 <div key={boundary} className="bg-white border border-gray-200 rounded p-3">
 <div className="text-xs text-gray-500 uppercase mb-1">
 {boundary} Setback
 </div>
 <div className="font-bold text-lg text-gray-900">
 {values.length > 0 ? (
 min === max ? `${min}m` : `${min}-${max}m`
 ) : (
 <span className="text-gray-400">N/A</span>
 )}
 </div>
 {values.length > 1 && (
 <div className="text-xs text-gray-500 mt-1">
 {values.length} variations
 </div>
 )}
 </div>
 );
 })}
 </div>

 {/* Detailed provisions */}
 <div className="space-y-2">
 {setbacks.map((setback: any, idx: number) => (
 <div key={idx} className="bg-gray-50 rounded p-3 text-sm">
 <div className="flex justify-between items-start mb-2">
 <div>
 <span className="font-medium capitalize">{setback.boundary_type}</span>
 <span className="ml-2 text-gray-600">{setback.value}m</span>
 </div>
 <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
 {setback.authority}
 </span>
 </div>
 <div className="text-xs text-gray-600">
 {setback.clause_reference}
 </div>
 {setback.full_text && (
 <div className="mt-2 text-xs text-gray-500 italic">
 {setback.full_text}
 </div>
 )}
 </div>
 ))}
 </div>

 {/* Referenced Legislation */}
 <ReferencedLegislationAccordion 
 setbacks={setbacks}
 />
 </div>
 )}
 </div>
 );
 })}
 </div>

 {/* Comparison Table (optional enhancement) */}
 {selectedTypes.length > 1 && (
 <div className="mt-6 p-4 bg-gray-50 rounded-lg">
 <h3 className="font-semibold mb-3">Quick Comparison</h3>
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b">
 <th className="text-left py-2">Development Type</th>
 <th className="text-center">Front</th>
 <th className="text-center">Side</th>
 <th className="text-center">Rear</th>
 </tr>
 </thead>
 <tbody>
 {selectedTypes.map(devType => {
 const setbacks = groupedSetbacks[devType] || [];
 const front = setbacks.find((s: any) => s.boundary_type === 'front');
 const side = setbacks.find((s: any) => s.boundary_type === 'side');
 const rear = setbacks.find((s: any) => s.boundary_type === 'rear');
 
 return (
 <tr key={devType} className="border-b">
 <td className="py-2">{DEV_TYPE_NAMES[devType]}</td>
 <td className="text-center">{front?.value || '-'}m</td>
 <td className="text-center">{side?.value || '-'}m</td>
 <td className="text-center">{rear?.value || '-'}m</td>
 </tr>
 );
 })}
 </tbody>
 </table>
 </div>
 )}
 </div>
 );
}
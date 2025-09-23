'use client';

import { useState, useEffect } from 'react';
import { Check, Info, Building, Home, Users, Store } from 'lucide-react';

interface DevelopmentType {
 id: string;
 name: string;
 description: string;
 icon: any;
 permitted: boolean;
}

interface DevelopmentTypeSelectorProps {
 zone: string;
 onSelectionChange: (selected: string[]) => void;
}

const ZONE_DEVELOPMENT_TYPES: Record<string, DevelopmentType[]> = {
 'R1': [
 { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
 { id: 'dual_occupancy', name: 'Dual Occupancy', description: 'Two dwellings on one lot', icon: Users, permitted: true },
 ],
 'R2': [
 { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
 { id: 'dual_occupancy', name: 'Dual Occupancy', description: 'Two dwellings on one lot', icon: Users, permitted: true },
 { id: 'multi_dwelling_housing', name: 'Multi Dwelling Housing', description: 'Townhouses, villas (3+ dwellings)', icon: Building, permitted: true },
 { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'Apartment building', icon: Building, permitted: true },
 ],
 'R3': [
 { id: 'dwelling_house', name: 'Dwelling House', description: 'Single residential dwelling', icon: Home, permitted: true },
 { id: 'multi_dwelling_housing', name: 'Multi Dwelling Housing', description: 'Townhouses, villas', icon: Building, permitted: true },
 { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'Apartment building', icon: Building, permitted: true },
 { id: 'shop_top_housing', name: 'Shop Top Housing', description: 'Residential above retail', icon: Store, permitted: true },
 ],
 'R4': [
 { id: 'residential_flat_building', name: 'Residential Flat Building', description: 'High density apartments', icon: Building, permitted: true },
 { id: 'shop_top_housing', name: 'Shop Top Housing', description: 'Mixed use development', icon: Store, permitted: true },
 ],
};

export function DevelopmentTypeSelector({ zone, onSelectionChange }: DevelopmentTypeSelectorProps) {
 const developmentTypes = ZONE_DEVELOPMENT_TYPES[zone] || [];
 const [selected, setSelected] = useState<string[]>(developmentTypes.map(dt => dt.id));

 useEffect(() => {
 onSelectionChange(selected);
 }, [selected, onSelectionChange]);

 const toggleSelection = (typeId: string) => {
 setSelected(prev => 
 prev.includes(typeId) 
 ? prev.filter(id => id !== typeId)
 : [...prev, typeId]
 );
 };

 if (developmentTypes.length === 0) {
 return null;
 }

 return (
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <div className="flex items-start gap-2 mb-3">
 <Info className="h-5 w-5 text-blue-600 mt-0.5" />
 <div>
 <h3 className="font-semibold text-gray-900">
 Development Types Permitted in Zone {zone}
 </h3>
 <p className="text-sm text-gray-600 mt-1">
 Select the development types you want to see requirements for:
 </p>
 </div>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
 {developmentTypes.map(type => {
 const Icon = type.icon;
 const isSelected = selected.includes(type.id);
 
 return (
 <button
 key={type.id}
 onClick={() => toggleSelection(type.id)}
 className={`
 flex items-start gap-3 p-3 rounded-lg border-2 transition-all
 ${isSelected 
 ? 'border-blue-500 bg-white shadow-sm' 
 : 'border-gray-200 bg-gray-50 opacity-60'
 }
 `}
 >
 <div className={`mt-0.5 ${isSelected ? 'text-blue-600' : 'text-gray-400'}`}>
 {isSelected ? (
 <div className="relative">
 <Icon className="h-5 w-5" />
 <Check className="h-3 w-3 absolute -bottom-1 -right-1 text-green-600" />
 </div>
 ) : (
 <Icon className="h-5 w-5" />
 )}
 </div>
 <div className="flex-1 text-left">
 <div className="font-medium text-sm text-gray-900">
 {type.name}
 </div>
 <div className="text-xs text-gray-500 mt-0.5">
 {type.description}
 </div>
 </div>
 </button>
 );
 })}
 </div>

 <div className="mt-4 text-xs text-gray-500 flex items-center gap-1">
 <Info className="h-3 w-3" />
 All types are shown by default. Uncheck types not relevant to your project.
 </div>
 </div>
 );
}
'use client';

import { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';

interface DevelopmentSelectorProps {
 value?: string;
 onChange?: (value: string) => void;
 zoneCode?: string;
}

// Development types by zone
const ZONE_DEVELOPMENT_TYPES: Record<string, Array<{ value: string; label: string; description?: string }>> = {
 'R1': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling' },
 { value: 'dual_occupancy', label: 'Dual Occupancy', description: 'Two dwellings on one lot' },
 { value: 'secondary_dwelling', label: 'Secondary Dwelling', description: 'Granny flat or secondary dwelling' },
 { value: 'group_home', label: 'Group Home', description: 'Small-scale residential care' },
 ],
 'R2': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling' },
 { value: 'dual_occupancy', label: 'Dual Occupancy', description: 'Two dwellings on one lot' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, villas (3+ dwellings)' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartment building' },
 { value: 'boarding_house', label: 'Boarding House', description: 'Affordable rental accommodation' },
 ],
 'R3': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, villas' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartment building' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Residential above retail' },
 { value: 'seniors_housing', label: 'Seniors Housing', description: 'Housing for seniors or people with disabilities' },
 ],
 'R4': [
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'High density apartments' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Mixed use development' },
 { value: 'seniors_housing', label: 'Seniors Housing', description: 'High density seniors housing' },
 { value: 'boarding_house', label: 'Boarding House', description: 'High density affordable housing' },
 ],
 'E1': [
 { value: 'commercial_premises', label: 'Commercial Premises', description: 'Shops, offices, restaurants, cafés with council consent' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartments, generally above ground-floor retail' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, terrace-style as part of mixed-use developments' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Apartments above retail/commercial' },
 { value: 'subdivision', label: 'Subdivision', description: 'Only with consent and in conjunction with other permitted uses' },
 ],
 // Default options for unknown zones
 'DEFAULT': [
 { value: 'dwelling_house', label: 'Single Dwelling House' },
 { value: 'dual_occupancy', label: 'Dual Occupancy' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing' },
 { value: 'residential_flat_building', label: 'Residential Flat Building' },
 { value: 'commercial_premises', label: 'Commercial Development' },
 { value: 'industrial', label: 'Industrial Development' },
 { value: 'subdivision', label: 'Subdivision' },
 ],
};

export function DevelopmentSelectorEnhanced({
 value,
 onChange,
 zoneCode
}: DevelopmentSelectorProps) {
 const { flags } = useFeatureFlags();
 const [localValue, setLocalValue] = useState(value || 'dual_occupancy');

 // Sync localValue with prop changes
 useEffect(() => {
   if (value && value !== localValue) {
     setLocalValue(value);
   }
 }, [value]);
 const [currentZone, setCurrentZone] = useState<string>('');
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 // Listen for property zone updates
 useEffect(() => {
 try {
 const handleAddressSelected = (event: CustomEvent) => {
 console.log('Development selector received address event');
 setError(null); // Clear errors on new selection
 };

 window.addEventListener('addressSelected', handleAddressSelected as EventListener);
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener);
 };
 } catch (err) {
 setError('Failed to set up event listeners');
 console.error('Development selector event setup error:', err);
 }
 }, []);

 // Update current zone when prop changes
 useEffect(() => {
 try {
 if (zoneCode && zoneCode !== currentZone) {
 setLoading(true);
 setCurrentZone(zoneCode);
 console.log('Development types updated for zone:', zoneCode);
 setError(null);
 setLoading(false);
 }
 } catch (err) {
 setError('Failed to update zone information');
 console.error('Zone update error:', err);
 setLoading(false);
 }
 }, [zoneCode, currentZone]);

 // Get development types for current zone
 const getDevelopmentTypes = () => {
 if (currentZone && ZONE_DEVELOPMENT_TYPES[currentZone]) {
 return ZONE_DEVELOPMENT_TYPES[currentZone];
 }
 return ZONE_DEVELOPMENT_TYPES['DEFAULT'];
 };

 const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
 const newValue = e.target.value;
 setLocalValue(newValue);

 // Notify parent component
 if (onChange) {
 onChange(newValue);
 }

 // Dispatch custom event for other components to listen
 window.dispatchEvent(new CustomEvent('developmentTypeChanged', {
 detail: {
 developmentType: newValue,
 zone: currentZone
 }
 }));

 console.log(' Development type changed:', newValue);
 };

 const developmentTypes = getDevelopmentTypes();
 const selectedType = developmentTypes.find(t => t.value === localValue);

 // If feature flag is off, show the old static component
 if (!flags.newDevelopmentSelector) {
 return (
 <Card className="p-6 shadow-sm">
 <div className="space-y-4">
 <label className="text-sm font-semibold text-gray-700">Development Type:</label>
 <div className="relative">
 <select className="w-full p-3 border border-gray-300 rounded-md bg-white text-base appearance-none pr-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium">
 <option>Dual Occupancy</option>
 <option>Single Dwelling</option>
 <option>Multi Dwelling Housing</option>
 <option>Subdivision</option>
 <option>Commercial Development</option>
 <option>Industrial Development</option>
 </select>
 <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
 </div>
 </div>
 </Card>
 );
 }

 // Enhanced version with feature flag enabled
 return (
 <Card className="p-6 shadow-sm border-l-4 border-l-blue-500">
 <div className="space-y-4">
 <div className="flex justify-between items-start">
 <label className="text-sm font-semibold text-gray-700">
 Development Type:
 {currentZone && (
 <span className="ml-2 text-xs font-normal text-gray-500">
 (Zone {currentZone})
 </span>
 )}
 </label>
 <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Dynamic</span>
 </div>

 <div className="relative">
 <select
 value={localValue}
 onChange={handleChange}
 className="w-full p-3 border border-gray-300 rounded-md bg-white text-base appearance-none pr-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium transition-colors"
 >
 {developmentTypes.map(type => (
 <option key={type.value} value={type.value}>
 {type.label}
 </option>
 ))}
 </select>
 <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
 </div>

 {selectedType?.description && (
 <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
 {selectedType.description}
 </div>
 )}

 {!currentZone && (
 <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
 Select a property to see zone-specific development types
 </div>
 )}
 </div>
 </Card>
 );
}
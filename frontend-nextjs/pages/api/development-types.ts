import { NextApiRequest, NextApiResponse } from 'next';
import { DevelopmentType } from '@/components/development/types';
import { PRPK7DatabaseClient } from '@/lib/database/prp-k7-client';

// Zone-based development type mapping from PRP-K7 database
const ZONE_DEVELOPMENT_MAPPING: Record<string, Array<{ value: string; label: string; description: string; category: string; }>> = {
 'E1': [
 { value: 'commercial_premises', label: 'Commercial Premises', description: 'Shops, offices, restaurants, cafés with council consent', category: 'commercial' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartments, generally above ground-floor retail', category: 'residential' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, terrace-style as part of mixed-use developments', category: 'residential' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Apartments above retail/commercial', category: 'mixed' },
 { value: 'subdivision', label: 'Subdivision', description: 'Only with consent and in conjunction with other permitted uses', category: 'mixed' },
 ],
 'R1': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling', category: 'residential' },
 { value: 'dual_occupancy', label: 'Dual Occupancy', description: 'Two dwellings on one lot', category: 'residential' },
 { value: 'secondary_dwelling', label: 'Secondary Dwelling', description: 'Granny flat or secondary dwelling', category: 'residential' },
 { value: 'group_home', label: 'Group Home', description: 'Small-scale residential care', category: 'residential' },
 ],
 'R2': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling', category: 'residential' },
 { value: 'dual_occupancy', label: 'Dual Occupancy', description: 'Two dwellings on one lot', category: 'residential' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, villas (3+ dwellings)', category: 'residential' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartment building', category: 'residential' },
 { value: 'boarding_house', label: 'Boarding House', description: 'Affordable rental accommodation', category: 'residential' },
 ],
 'R3': [
 { value: 'dwelling_house', label: 'Single Dwelling House', description: 'Single residential dwelling', category: 'residential' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing', description: 'Townhouses, villas', category: 'residential' },
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'Apartment building', category: 'residential' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Residential above retail', category: 'mixed' },
 { value: 'seniors_housing', label: 'Seniors Housing', description: 'Housing for seniors or people with disabilities', category: 'residential' },
 ],
 'R4': [
 { value: 'residential_flat_building', label: 'Residential Flat Building', description: 'High density apartments', category: 'residential' },
 { value: 'shop_top_housing', label: 'Shop Top Housing', description: 'Mixed use development', category: 'mixed' },
 { value: 'seniors_housing', label: 'Seniors Housing', description: 'High density seniors housing', category: 'residential' },
 { value: 'boarding_house', label: 'Boarding House', description: 'High density affordable housing', category: 'residential' },
 ],
};

// Fallback development types for unknown zones
const fallbackDevelopmentTypes: DevelopmentType[] = [
 {
 id: '1',
 code: 'RFB',
 name: 'Residential Flat Building',
 description: 'A building containing multiple dwellings, but not a boarding house',
 category: 'residential',
 complianceRequirements: ['Building Height', 'Floor Space Ratio', 'Setbacks', 'Parking'],
 applicableZones: ['R3', 'R4', 'B1', 'B4'],
 minimumLotSize: 600,
 maximumHeight: 24,
 isEnabled: true,
 },
 {
 id: '2',
 code: 'SFD',
 name: 'Single Family Dwelling',
 description: 'A detached house for occupation by a single family',
 category: 'residential',
 complianceRequirements: ['Building Height', 'Setbacks', 'Site Coverage'],
 applicableZones: ['R1', 'R2', 'R3'],
 minimumLotSize: 450,
 maximumHeight: 9,
 isEnabled: true,
 },
 {
 id: '3',
 code: 'CP',
 name: 'Commercial Premises',
 description: 'Building or place used for commercial purposes',
 category: 'commercial',
 complianceRequirements: ['Floor Space Ratio', 'Parking', 'Access'],
 applicableZones: ['B1', 'B2', 'B3', 'B4'],
 isEnabled: true,
 },
 {
 id: '4',
 code: 'TH',
 name: 'Townhouse',
 description: 'One of a group of attached dwellings, each on its own lot',
 category: 'residential',
 complianceRequirements: ['Building Height', 'Setbacks', 'Private Open Space'],
 applicableZones: ['R2', 'R3'],
 minimumLotSize: 300,
 maximumHeight: 12,
 isEnabled: true,
 },
 {
 id: '5',
 code: 'MU',
 name: 'Mixed Use Development',
 description: 'Building containing both residential and commercial uses',
 category: 'mixed',
 complianceRequirements: ['Floor Space Ratio', 'Building Height', 'Parking', 'Acoustic Privacy'],
 applicableZones: ['B1', 'B2', 'B4'],
 minimumLotSize: 800,
 isEnabled: true,
 },
];

async function getDevelopmentTypes(params: {
 propertyId?: string;
 zoning?: string;
 category?: string;
}): Promise<DevelopmentType[]> {
 // In a real implementation, this would query a database
 let filtered = [...fallbackDevelopmentTypes];

 // Filter by zoning if provided
 if (params.zoning) {
 filtered = filtered.filter(dev =>
 dev.applicableZones.includes(params.zoning!) || dev.applicableZones.includes('*')
 );
 }

 // Filter by category if provided
 if (params.category) {
 filtered = filtered.filter(dev => dev.category === params.category);
 }

 return filtered;
}

export default async function handler(
 req: NextApiRequest,
 res: NextApiResponse
) {
 if (req.method !== 'GET') {
 return res.status(405).json({ error: 'Method not allowed' });
 }

 try {
 const { zone, propertyId, category } = req.query;

 console.log(`[API] Getting development types for zone: ${zone}, property: ${propertyId}, category: ${category}`);

 // Use zone-based filtering from regulatory data
 let allowedTypes = [];

 if (zone && ZONE_DEVELOPMENT_MAPPING[zone as string]) {
 allowedTypes = ZONE_DEVELOPMENT_MAPPING[zone as string];
 console.log(`[API] Found ${allowedTypes.length} development types for zone ${zone}`);
 } else {
 // Fallback to database query for unknown zones
 try {
 const client = new PRPK7DatabaseClient();
 const dbTypes = await client.getPermittedDevelopmentTypes(zone as string);
 console.log(`[API] Database returned ${dbTypes.length} types for zone ${zone}`);

 // Map database results to our format
 allowedTypes = dbTypes.map(type => ({
 value: type,
 label: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
 description: `${type.replace(/_/g, ' ')} permitted in zone ${zone}`,
 category: type.includes('residential') ? 'residential' :
 type.includes('commercial') ? 'commercial' :
 type.includes('industrial') ? 'industrial' : 'mixed'
 }));
 } catch (dbError) {
 console.warn(`[API] Database query failed for zone ${zone}, using fallback:`, dbError);
 allowedTypes = fallbackDevelopmentTypes.map(type => ({
 value: type.code.toLowerCase(),
 label: type.name,
 description: type.description,
 category: type.category
 }));
 }
 }

 // Filter by category if specified
 if (category) {
 allowedTypes = allowedTypes.filter(type => type.category === category);
 }

 // Convert to DevelopmentType format
 const developmentTypes: DevelopmentType[] = allowedTypes.map((type, index) => ({
 id: (index + 1).toString(),
 code: type.value.toUpperCase(),
 name: type.label,
 description: type.description,
 category: type.category as 'residential' | 'commercial' | 'industrial' | 'mixed',
 complianceRequirements: ['Building Height', 'Setbacks', 'Floor Space Ratio'],
 applicableZones: [zone as string],
 isEnabled: true,
 }));

 console.log(`[API] Returning ${developmentTypes.length} development types for zone ${zone}`);

 res.status(200).json({
 success: true,
 data: developmentTypes,
 zone: zone,
 totalTypes: developmentTypes.length
 });

 } catch (error) {
 console.error('Development types API error:', error);
 res.status(500).json({
 error: 'Internal server error',
 message: process.env.NODE_ENV === 'development' ? (error instanceof Error ? error.message : String(error)) : 'Failed to load development types'
 });
 }
}

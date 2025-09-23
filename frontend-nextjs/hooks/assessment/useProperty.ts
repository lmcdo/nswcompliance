/**
 * Property data hook using existing property API
 */

import { useState, useEffect } from 'react';
import { assessmentAPI } from '@/lib/assessment/api-client';
import { PropertyData } from '@/lib/assessment/types';

export function useProperty(address: string) {
 const [property, setProperty] = useState<PropertyData | null>(null);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 useEffect(() => {
 if (!address) {
 setProperty(null);
 return;
 }

 async function loadProperty() {
 setLoading(true);
 setError(null);

 try {
 // Use the existing property API
 const data = await assessmentAPI.getPropertyBasic(address);

 if (data.data) {
 setProperty({
 propId: data.data.propertyData.propId,
 address: data.data.propertyData.address,
 zone: data.data.constraints.zone || 'Unknown',
 lga: data.data.constraints.lga || 'Unknown',
 area: data.data.propertyData.propertyArea || 'Unknown',
 landValue: data.data.propertyData.landValue,
 heritage: data.data.constraints.heritage || false
 });
 } else {
 setError('Property not found');
 }
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to load property');
 } finally {
 setLoading(false);
 }
 }

 loadProperty();
 }, [address]);

 return { property, loading, error };
}

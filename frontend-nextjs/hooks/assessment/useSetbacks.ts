/**
 * Setbacks calculation hook using existing setbacks API
 */

import { useState, useEffect } from 'react';
import { assessmentAPI } from '@/lib/assessment/api-client';

export function useSetbacks(propertyId?: number, zone?: string) {
 const [setbacks, setSetbacks] = useState<any>(null);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 useEffect(() => {
 if (!propertyId || !zone) {
 setSetbacks(null);
 return;
 }

 async function loadSetbacks() {
 setLoading(true);
 setError(null);

 try {
 const data = await assessmentAPI.calculateSetbacks(propertyId!, zone!);
 setSetbacks(data);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to calculate setbacks');
 } finally {
 setLoading(false);
 }
 }

 loadSetbacks();
 }, [propertyId, zone]);

 return { setbacks, loading, error };
}

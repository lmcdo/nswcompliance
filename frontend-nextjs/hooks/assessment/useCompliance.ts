/**
 * Compliance checking hook using existing compliance APIs
 */

import { useState, useEffect } from 'react';
import { assessmentAPI } from '@/lib/assessment/api-client';

export function useCompliance({
 propertyId,
 zone,
 developmentType,
 assessmentDate
}: {
 propertyId?: number;
 zone?: string;
 developmentType?: string;
 assessmentDate?: string;
}) {
 const [compliance, setCompliance] = useState<any>(null);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);

 useEffect(() => {
 if (!propertyId || !zone || !developmentType) {
 setCompliance(null);
 return;
 }

 async function loadCompliance() {
 setLoading(true);
 setError(null);

 try {
 const data = await assessmentAPI.getCompliance({
 propertyId,
 zone,
 developmentType,
 assessmentDate
 });

 setCompliance(data);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to load compliance data');
 } finally {
 setLoading(false);
 }
 }

 loadCompliance();
 }, [propertyId, zone, developmentType, assessmentDate]);

 return { compliance, loading, error };
}

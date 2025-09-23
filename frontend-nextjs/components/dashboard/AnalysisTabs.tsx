// components/dashboard/AnalysisTabs.tsx
'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PreciseSetbackCalculator } from '@/components/analysis/PreciseSetbackCalculator';
import type { PropertyData, LotGeometry } from '@/types/property';

interface AnalysisTabsProps {
 property: PropertyData | null;
 lotGeometry: LotGeometry | null;
 loading: {
 property: boolean;
 setbacks: boolean;
 heritage: boolean;
 pathways: boolean;
 };
 error: {
 property: string | null;
 setbacks: string | null;
 heritage: string | null;
 pathways: string | null;
 };
}

export function AnalysisTabs({ 
 property, 
 lotGeometry, 
 loading, 
 error 
}: AnalysisTabsProps) {
 const [activeTab, setActiveTab] = useState('setbacks');

 if (!property) {
 return (
 <div className="analysis-tabs p-8">
 <div className="text-center text-gray-500">
 <p className="text-lg mb-2">Ready for Analysis</p>
 <p className="text-sm">
 Enter a property address to begin compliance analysis with:
 </p>
 <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
 <div className="p-3 bg-blue-50 rounded-lg">
 <div className="font-medium text-blue-900"> Precise Setbacks</div>
 <div className="text-blue-700 mt-1">Centimeter-level calculations</div>
 </div>
 <div className="p-3 bg-green-50 rounded-lg">
 <div className="font-medium text-green-900"> Explanations</div>
 <div className="text-green-700 mt-1">WHY requirements exist</div>
 </div>
 <div className="p-3 bg-purple-50 rounded-lg">
 <div className="font-medium text-purple-900"> Heritage</div>
 <div className="text-purple-700 mt-1">Protection logic & constraints</div>
 </div>
 <div className="p-3 bg-orange-50 rounded-lg">
 <div className="font-medium text-orange-900"> Pathways</div>
 <div className="text-orange-700 mt-1">Optimal development strategy</div>
 </div>
 </div>
 </div>
 </div>
 );
 }

 return (
 <div className="analysis-tabs">
 <Tabs value={activeTab} onValueChange={setActiveTab}>
 <TabsList className="grid w-full grid-cols-4">
 <TabsTrigger value="setbacks" className="text-sm">
 Precise Setbacks
 </TabsTrigger>
 <TabsTrigger value="explanations" className="text-sm">
 Explanations
 </TabsTrigger>
 <TabsTrigger value="heritage" className="text-sm">
 Heritage
 </TabsTrigger>
 <TabsTrigger value="pathways" className="text-sm">
 Pathways
 </TabsTrigger>
 </TabsList>

 <TabsContent value="setbacks" className="mt-6">
 <PreciseSetbackCalculator 
 property={property}
 lotGeometry={lotGeometry}
 loading={loading.setbacks}
 error={error.setbacks}
 />
 </TabsContent>

 <TabsContent value="explanations" className="mt-6">
 <div className="p-8 text-center text-gray-500">
 <h3 className="text-lg font-semibold mb-2">Compliance Explanations</h3>
 <p className="mb-4">
 Understand WHY requirements exist using 514 "because" relationships
 </p>
 <div className="text-sm bg-blue-50 p-4 rounded-lg">
 Coming Soon: Intelligent requirement explanations with reasoning
 </div>
 </div>
 </TabsContent>

 <TabsContent value="heritage" className="mt-6">
 <div className="p-8 text-center text-gray-500">
 <h3 className="text-lg font-semibold mb-2">Heritage Intelligence</h3>
 <p className="mb-4">
 Detailed heritage analysis using 788 controls + protection logic
 </p>
 <div className="text-sm bg-purple-50 p-4 rounded-lg">
 Coming Soon: Heritage constraints with protection reasoning
 </div>
 </div>
 </TabsContent>

 <TabsContent value="pathways" className="mt-6">
 <div className="p-8 text-center text-gray-500">
 <h3 className="text-lg font-semibold mb-2">Development Pathways</h3>
 <p className="mb-4">
 Strategic pathway optimization using structured criteria
 </p>
 <div className="text-sm bg-orange-50 p-4 rounded-lg">
 Coming Soon: Optimal development pathway recommendations
 </div>
 </div>
 </TabsContent>
 </Tabs>
 </div>
 );
}
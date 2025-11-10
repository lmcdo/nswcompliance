'use client';

import { useState } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { FeatureFlags } from '@/lib/feature-flags';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Settings, Eye, EyeOff, RotateCcw } from 'lucide-react';

export function FeatureFlagDebugPanel() {
 const { flags, updateFlag, resetFlags, isLoading, error } = useFeatureFlags();
 const [isVisible, setIsVisible] = useState(false);

 // Disabled - use browser console instead
 return null;

 // Only show in development
 if (process.env.NODE_ENV !== 'development') {
 return null;
 }

 if (!isVisible) {
 return (
 <div className="fixed bottom-4 right-4 z-50">
 <Button
 onClick={() => setIsVisible(true)}
 variant="outline"
 size="sm"
 className="bg-blue-500 text-white hover:bg-blue-600 border-blue-500"
 >
 <Settings className="h-4 w-4 mr-1" />
 Feature Flags
 </Button>
 </div>
 );
 }

 const flagCategories = {
 Migration: [
 'authoritativeRouteMigration',
 'newDevelopmentSelector',
 'newComplianceStatus',
 'newComplianceChecklist'
 ] as Array<keyof FeatureFlags>,
 Infrastructure: [
 'unifiedStateManagement',
 'legacyRouteFallback'
 ] as Array<keyof FeatureFlags>,
 Performance: [
 'enableCaching',
 'enableAnalytics'
 ] as Array<keyof FeatureFlags>
 };

 const formatFlagName = (flag: string): string => {
 return flag
 .replace(/([A-Z])/g, ' $1')
 .replace(/^./, str => str.toUpperCase())
 .trim();
 };

 return (
 <div className="fixed bottom-4 right-4 z-50 w-96">
 <Card className="shadow-lg border-2 border-blue-200 bg-white">
 <CardHeader className="pb-3">
 <div className="flex items-center justify-between">
 <CardTitle className="text-lg flex items-center gap-2">
 <Settings className="h-5 w-5 text-blue-500" />
 Feature Flags
 <Badge variant="outline" className="text-xs">
 DEV
 </Badge>
 </CardTitle>
 <div className="flex gap-2">
 <Button
 onClick={resetFlags}
 variant="outline"
 size="sm"
 className="text-xs"
 >
 <RotateCcw className="h-3 w-3 mr-1" />
 Reset
 </Button>
 <Button
 onClick={() => setIsVisible(false)}
 variant="outline"
 size="sm"
 >
 <EyeOff className="h-4 w-4" />
 </Button>
 </div>
 </div>
 </CardHeader>

 <CardContent className="space-y-4 max-h-96 overflow-y-auto">
 {error && (
 <div className="text-red-600 text-sm p-2 bg-red-50 rounded">
 Error: {error}
 </div>
 )}

 {isLoading ? (
 <div className="text-center py-4">
 <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
 <p className="text-sm text-gray-500 mt-2">Loading flags...</p>
 </div>
 ) : (
 Object.entries(flagCategories).map(([category, categoryFlags]) => (
 <div key={category} className="space-y-2">
 <h4 className="font-medium text-sm text-gray-700 border-b border-gray-200 pb-1">
 {category}
 </h4>

 <div className="space-y-2">
 {categoryFlags.map((flag) => (
 <div
 key={flag}
 className="flex items-center justify-between p-2 rounded hover:bg-gray-50"
 >
 <div className="flex-1">
 <div className="text-sm font-medium text-gray-900">
 {formatFlagName(flag)}
 </div>
 <div className="text-xs text-gray-500">
 {flag}
 </div>
 </div>

 <div className="flex items-center gap-2">
 <Badge
 variant={flags[flag] ? "default" : "secondary"}
 className={`text-xs ${
 flags[flag]
 ? "bg-green-100 text-green-800 border-green-200"
 : "bg-gray-100 text-gray-600 border-gray-200"
 }`}
 >
 {flags[flag] ? 'ON' : 'OFF'}
 </Badge>

 <Switch
 checked={flags[flag] || false}
 onCheckedChange={(checked) => updateFlag(flag, checked)}
 className="scale-75"
 />
 </div>
 </div>
 ))}
 </div>
 </div>
 ))
 )}

 <div className="pt-2 border-t border-gray-200">
 <div className="text-xs text-gray-500 space-y-1">
 <div>Environment: <span className="font-mono">{process.env.NODE_ENV}</span></div>
 <div>
 Enabled: {Object.values(flags).filter(Boolean).length} / {Object.keys(flags).length}
 </div>
 </div>
 </div>
 </CardContent>
 </Card>
 </div>
 );
}
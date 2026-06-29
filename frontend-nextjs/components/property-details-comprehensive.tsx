"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronRight, MapPin, Ruler, Square, Plane, Flag, AlertTriangle, Crosshair } from "lucide-react"

interface BattleaxeInfo {
  isBattleaxe: boolean;
  confidence: number;
  accessWayWidth: number;
  accessWayLength: number;
  mainLotWidth: number;
  mainLotArea: number;
  meetsMinimumRequirements: boolean;
  complianceIssues: string[];
}

interface LotDimensions {
 area: number;
 frontage: number;
 depth: number;
 confidence: number;
 notes?: string[];
 lotType?: 'rectangular' | 'battleaxe' | 'irregular';
 battleaxe?: BattleaxeInfo;
}

interface AnefInfo {
  inAnefZone: boolean;
  anefLevel: number | null;
  airport: {
    code: string;
    name: string;
    version: string;
  } | null;
  buildingAcceptability: Array<{
    buildingType: string;
    displayName: string;
    status: 'acceptable' | 'conditional' | 'unacceptable';
  }> | null;
}

interface CornerLotInfo {
  isCornerLot: boolean;
  adjacentRoads: string[];
  roadCount: number;
  confidence: number;
  error?: string;
}

interface PropertyData {
 constraints?: any;
 propertyArea?: string;
 lotDimensions?: LotDimensions;
 anefData?: AnefInfo | null;
 cornerLot?: CornerLotInfo | null;
 address?: string;
}

interface PropertyDetailsComprehensiveProps {
 propertyData?: PropertyData;
 lepClauseData?: any;
}

export function PropertyDetailsComprehensive({ propertyData, lepClauseData }: PropertyDetailsComprehensiveProps) {
 const [isCardCollapsed, setIsCardCollapsed] = useState(false)

 if (!propertyData) {
   return null
 }

 return (
   <Card className="bg-gray-100 border-gray-200">
     <CardHeader className="cursor-pointer" onClick={() => setIsCardCollapsed(!isCardCollapsed)}>
       <CardTitle className="text-lg font-semibold flex items-center gap-2 text-gray-900">
         {isCardCollapsed ? <ChevronRight className="h-4 w-4 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 flex-shrink-0" />}
         <MapPin className="h-5 w-5 text-gray-700" />
         <span className="flex-1">Property Details</span>
       </CardTitle>
     </CardHeader>
     {!isCardCollapsed && (
     <CardContent className="space-y-2">
       {/* Property Summary */}
       <div className="border-b pb-3 mb-2">
         <p className="font-medium text-gray-900 text-sm mb-1">{propertyData.address}</p>
         <p className="text-xs text-gray-600">
           {propertyData.constraints?.lga || 'Unknown'} LGA
         </p>
       </div>

       {/* Lot Dimensions from Cadastre */}
       {propertyData.lotDimensions && (
         <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-2">
           <div className="flex items-center gap-2 mb-2">
             <Ruler className="h-4 w-4 text-amber-700" />
             <span className="text-sm font-semibold text-amber-900">Lot Dimensions</span>
             <Badge className="text-xs bg-amber-100 text-amber-800 border-amber-300">Cadastre</Badge>
           </div>
           <div className={`grid ${propertyData.lotDimensions.battleaxe?.isBattleaxe ? 'grid-cols-1' : 'grid-cols-3'} gap-1.5`}>
             <div className="bg-white rounded p-2 text-center border border-amber-100">
               <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                 <Square className="h-3 w-3" />
                 <span className="text-xs">Area</span>
               </div>
               <span className="text-base font-bold text-gray-900">
                 {propertyData.lotDimensions.area.toLocaleString(undefined, { maximumFractionDigits: 0 })}
               </span>
               <span className="text-xs text-gray-500 ml-0.5">m²</span>
             </div>
             {/* Rectangular frontage/depth are meaningless for an L-shaped battleaxe
                 (they classify arbitrary edges of the L). Suppress them and let the
                 battleaxe block below carry the real handle/head geometry. */}
             {!propertyData.lotDimensions.battleaxe?.isBattleaxe && (
               <>
                 <div className="bg-white rounded p-2 text-center border border-amber-100">
                   <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                     <Ruler className="h-3 w-3" />
                     <span className="text-xs">Frontage</span>
                   </div>
                   <span className="text-base font-bold text-gray-900">
                     {propertyData.lotDimensions.frontage.toFixed(1)}
                   </span>
                   <span className="text-xs text-gray-500 ml-0.5">m</span>
                 </div>
                 <div className="bg-white rounded p-2 text-center border border-amber-100">
                   <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                     <Ruler className="h-3 w-3 rotate-90" />
                     <span className="text-xs">Depth</span>
                   </div>
                   <span className="text-base font-bold text-gray-900">
                     {propertyData.lotDimensions.depth.toFixed(1)}
                   </span>
                   <span className="text-xs text-gray-500 ml-0.5">m</span>
                 </div>
               </>
             )}
           </div>
           {propertyData.lotDimensions.confidence < 0.8 && (
             <p className="text-xs text-amber-700 mt-2 italic">
               Note: Irregular lot shape - dimensions are estimates
             </p>
           )}
         </div>
       )}

       {/* Battleaxe Lot Detection */}
       {propertyData.lotDimensions?.battleaxe?.isBattleaxe && (
         <div className="bg-violet-50 border border-violet-200 rounded-lg p-3 mb-2">
           <div className="flex items-center gap-2 mb-2">
             <Flag className="h-4 w-4 text-violet-700" />
             <span className="text-sm font-semibold text-violet-900">Battleaxe Lot</span>
             <Badge className="text-xs bg-violet-100 text-violet-800 border-violet-300">
               Flag Lot
             </Badge>
             {!propertyData.lotDimensions.battleaxe.meetsMinimumRequirements && (
               <Badge className="text-xs bg-amber-100 text-amber-800 border-amber-300">
                 Below CDC Min
               </Badge>
             )}
           </div>
           <div className="grid grid-cols-2 gap-2 text-xs">
             <div className="bg-white rounded p-2 border border-violet-100">
               <span className="text-gray-500">Access Way</span>
               <p className="font-semibold text-gray-900">
                 {propertyData.lotDimensions.battleaxe.accessWayWidth}m wide
                 <span className="font-normal text-gray-500"> × {propertyData.lotDimensions.battleaxe.accessWayLength}m</span>
               </p>
               {propertyData.lotDimensions.battleaxe.accessWayWidth < 3 && (
                 <p className="text-red-600 text-xs mt-1">Below 3m minimum</p>
               )}
             </div>
             <div className="bg-white rounded p-2 border border-violet-100">
               <span className="text-gray-500">Main Lot</span>
               <p className="font-semibold text-gray-900">
                 {propertyData.lotDimensions.battleaxe.mainLotWidth}m wide
               </p>
               <p className="text-gray-500">{propertyData.lotDimensions.battleaxe.mainLotArea}m² area</p>
             </div>
           </div>
           {!propertyData.lotDimensions.battleaxe.meetsMinimumRequirements && (
             <div className="mt-2 pt-2 border-t border-red-200">
               <div className="flex items-start gap-1">
                 <AlertTriangle className="h-3 w-3 text-red-600 mt-0.5 flex-shrink-0" />
                 <div className="text-xs text-red-700">
                   <p className="font-medium">SEPP Housing 2021 Issues:</p>
                   <ul className="mt-1 space-y-0.5">
                     {propertyData.lotDimensions.battleaxe.complianceIssues.map((issue, i) => (
                       <li key={i}>• {issue}</li>
                     ))}
                   </ul>
                 </div>
               </div>
             </div>
           )}
           <p className="text-xs text-gray-500 mt-2 italic">
             SEPP Housing 2021 requires 3m min access way, 12m×12m min main lot
           </p>
         </div>
       )}

       {/* Corner Lot Detection */}
       {propertyData.cornerLot?.confidence === 1 && (
         <div className={`border rounded-lg p-3 mb-2 ${
           propertyData.cornerLot.isCornerLot
             ? 'bg-amber-50 border-amber-200'
             : 'bg-gray-50 border-gray-200'
         }`}>
           <div className="flex items-center gap-2 mb-2">
             <Crosshair className={`h-4 w-4 ${propertyData.cornerLot.isCornerLot ? 'text-amber-700' : 'text-gray-500'}`} />
             <span className={`text-sm font-semibold ${propertyData.cornerLot.isCornerLot ? 'text-amber-900' : 'text-gray-700'}`}>
               {propertyData.cornerLot.isCornerLot ? 'Corner Lot' : 'Not a Corner Lot'}
             </span>
             {propertyData.cornerLot.isCornerLot && (
               <Badge className="text-xs bg-amber-100 text-amber-800 border-amber-300">
                 {propertyData.cornerLot.roadCount} Roads
               </Badge>
             )}
           </div>
           {propertyData.cornerLot.isCornerLot && propertyData.cornerLot.adjacentRoads.length > 0 && (
             <div className="text-xs space-y-1">
               <p className="text-amber-800">
                 <span className="font-medium">Adjacent roads:</span>{' '}
                 {propertyData.cornerLot.adjacentRoads.join(', ')}
               </p>
               <p className="text-amber-700 italic mt-2">
                 Secondary street setback: 3m (vs 6m rear for non-corner)
               </p>
             </div>
           )}
           {!propertyData.cornerLot.isCornerLot && propertyData.cornerLot.adjacentRoads.length > 0 && (
             <p className="text-xs text-gray-600">
               Adjacent road: {propertyData.cornerLot.adjacentRoads[0]}
             </p>
           )}
         </div>
       )}

     </CardContent>
     )}
   </Card>
 )
}
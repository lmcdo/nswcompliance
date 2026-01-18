"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, MapPin, Calendar, FileText, Zap, TreePine, Building, Shield, ExternalLink, Ruler, Square } from "lucide-react"

interface PlanningLayer {
 id: string;
 layerName: string;
 results: any[];
}

interface LotDimensions {
 area: number;
 frontage: number;
 depth: number;
 confidence: number;
 notes?: string[];
}

interface PropertyData {
 planningLayers?: PlanningLayer[];
 constraints?: any;
 fsrSource?: any;
 heightSource?: any;
 environmental?: any;
 heritage?: any;
 propertyArea?: string;
 lotDimensions?: LotDimensions;
 address?: string;
}

interface PropertyDetailsComprehensiveProps {
 propertyData: PropertyData;
 lepClauseData?: any;
}

export function PropertyDetailsComprehensive({ propertyData, lepClauseData }: PropertyDetailsComprehensiveProps) {
 const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set())
 const [isCardCollapsed, setIsCardCollapsed] = useState(false)

 const toggleLayer = (layerId: string) => {
 const newExpanded = new Set(expandedLayers)
 if (newExpanded.has(layerId)) {
 newExpanded.delete(layerId)
 } else {
 newExpanded.add(layerId)
 }
 setExpandedLayers(newExpanded)
 }

 const getLayerIcon = (layerName: string) => {
 switch (layerName) {
 case 'Land Zoning Map': return <Building className="h-4 w-4" />
 case 'Height of Buildings Map': return <Building className="h-4 w-4" />
 case 'Floor Space Ratio Map': return <Building className="h-4 w-4" />
 case 'Heritage Map': return <Shield className="h-4 w-4" />
 case 'Special Provisions': return <Zap className="h-4 w-4" />
 case 'Regional Plan Boundary': return <MapPin className="h-4 w-4" />
 case 'Greater Sydney Tree Canopy Cover 2019':
 case 'Greater Sydney Tree Canopy Cover 2022': return <TreePine className="h-4 w-4" />
 default: return <FileText className="h-4 w-4" />
 }
 }

 const formatValue = (key: string, value: any) => {
 if (value === null || value === undefined) return 'N/A'

 // Handle legislationUrl and other URL fields
 if ((key === 'legislationUrl' || key.toLowerCase().includes('url')) && typeof value === 'string' && value.startsWith('http')) {
 return (
 <a
 href={value}
 target="_blank"
 rel="noopener noreferrer"
 className="text-teal-600 hover:text-teal-700 underline inline-flex items-center gap-1"
 >
 View Legislation
 <ExternalLink className="h-3 w-3" />
 </a>
 )
 }

 // Handle Regional Plan Website links
 if (key === 'Regional Plan Website' && typeof value === 'string' && value.includes('&lt;a href=')) {
 const decoded = value.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
 const linkMatch = decoded.match(/<a href="([^"]+)">([^<]+)<\/a>/)
 if (linkMatch) {
 const [, url, text] = linkMatch
 return (
 <a
 href={url}
 target="_blank"
 rel="noopener noreferrer"
 className="text-teal-600 hover:text-teal-800 underline font-medium"
 >
 {text}
 </a>
 )
 }
 }

 if (typeof value === 'string' && value.includes('&lt;')) {
 return value.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
 }
 return String(value)
 }

 const getImportantFields = (result: any) => {
 const important = []

 // Key regulatory fields
 if (result['Zone']) important.push({ key: 'Zone', value: result['Zone'] })
 if (result['Maximum Building Height']) important.push({ key: 'Height', value: `${result['Maximum Building Height']}${result['Units'] || ''}` })
 if (result['Floor Space Ratio']) {
   // Always show FSR from Planning Portal
   important.push({ key: 'FSR', value: `${result['Floor Space Ratio']}:1` })

   // Check if there's a dev-type-specific LEP clause cap that overrides FSR calculation
   const lepClauseCap = lepClauseData?.capacity?.maxGFA;
   const lepSource = lepClauseData?.capacity?.gfaSource;

   if (lepClauseCap && lepSource && lepSource !== 'FSR calculation') {
     // Show LEP clause limit (overrides FSR calculation)
     important.push({ key: 'Maximum Gross Floor Area', value: `${lepClauseCap.toFixed(1)}m² (${lepSource})` })
   } else {
     // Calculate max GFA from FSR if lot area is available
     if (propertyData.propertyArea) {
       const lotArea = parseFloat(propertyData.propertyArea.replace(/[^\d.]/g, ''))
       const fsr = parseFloat(result['Floor Space Ratio'])
       if (!isNaN(lotArea) && !isNaN(fsr)) {
         const maxGFA = (fsr * lotArea).toFixed(1)
         important.push({ key: 'Maximum Gross Floor Area', value: `${maxGFA}m²` })
       }
     }
   }
 }
 if (result['Land Use']) important.push({ key: 'Use', value: result['Land Use'] })
 if (result['Legislative Clause']) important.push({ key: 'Clause', value: result['Legislative Clause'] })

 // Environmental/Special
 if (result['Class']) important.push({ key: 'Class', value: result['Class'] })
 if (result['Canopy %']) important.push({ key: 'Canopy', value: `${result['Canopy %']}%` })
 if (result['Type']) important.push({ key: 'Type', value: result['Type'] })

 return important
 }

 const getSecondaryFields = (result: any) => {
 const exclude = [
    'Zone', 'Maximum Building Height', 'Floor Space Ratio', 'Land Use', 'Legislative Clause', 'Class', 'Canopy %', 'Type', 'title',
    // Remove unhelpful metadata
    'Commenced Date', 'Currency Date', 'EPI Type', 'LGA Name', 'Published Date'
  ]
 return Object.entries(result).filter(([key, value]) => !exclude.includes(key) && value !== null && value !== undefined && value !== '')
 }

 if (!propertyData || !propertyData.planningLayers || propertyData.planningLayers.length === 0) {
   return (
     <Card className="bg-gray-100 border-gray-200">
       <CardHeader>
         <CardTitle className="text-lg font-semibold flex items-center gap-2">
           <FileText className="h-5 w-5" />
           Planning Layers Details
         </CardTitle>
       </CardHeader>
       <CardContent>
         <div className="text-sm text-gray-500">Loading comprehensive planning data...</div>
       </CardContent>
     </Card>
   )
 }

 // Define all expected NSW Planning Layers
 const expectedLayers = [
   'Heritage Map',
   'Floor Space Ratio Map',
   'Height of Buildings Map',
   'Acid Sulfate Soils Map',
   'Local Aboriginal Land Council',
   'Special Provisions',
   'Land Application Map',
   'Regional Plan Boundary',
   'Land Zoning Map',
   'Greater Sydney Tree Canopy Cover 2019',
   'Greater Sydney Tree Canopy Cover 2022',
   'Terrestrial Biodiversity Map'
 ]

 // Create map of actual layers
 const layerMap = new Map()
 propertyData.planningLayers?.forEach(layer => {
   layerMap.set(layer.layerName, layer)
 })

 return (
   <Card className="bg-teal-100 border-teal-300">
     <CardHeader className="cursor-pointer" onClick={() => setIsCardCollapsed(!isCardCollapsed)}>
       <CardTitle className="text-lg font-semibold flex items-center justify-between text-teal-900">
         <div className="flex items-center gap-2">
           <FileText className="h-5 w-5 text-teal-700" />
           NSW Planning Layers ({expectedLayers.length})
         </div>
         {isCardCollapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
       </CardTitle>
     </CardHeader>
     {!isCardCollapsed && (
     <CardContent className="space-y-2">
       {/* Property Compliance Info at top */}
       <div className="border-b pb-3 mb-2">
         <p className="font-medium text-gray-900 text-sm mb-1">{propertyData.address}</p>
         <p className="text-xs text-gray-600">
           {propertyData.constraints?.lga || 'Unknown'} LGA | {propertyData.constraints?.zone || 'Unknown'} | {propertyData.constraints?.maxHeight ? `${propertyData.constraints.maxHeight}m` : 'No height'} | {propertyData.constraints?.maxFsr ? `${propertyData.constraints.maxFsr}:1` : 'No FSR'} | Heritage: {propertyData.heritage?.isHeritage ? 'Yes' : 'No'} | Flood: {propertyData.constraints?.floodProne ? 'Yes' : 'No'} | {propertyData.constraints?.basixWater || 'N/A'} Water SEPP
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
           <div className="grid grid-cols-3 gap-3">
             <div className="bg-white rounded p-2 text-center border border-amber-100">
               <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                 <Square className="h-3 w-3" />
                 <span className="text-xs">Area</span>
               </div>
               <span className="text-lg font-bold text-gray-900">
                 {propertyData.lotDimensions.area.toLocaleString(undefined, { maximumFractionDigits: 0 })}
               </span>
               <span className="text-xs text-gray-500 ml-1">m²</span>
             </div>
             <div className="bg-white rounded p-2 text-center border border-amber-100">
               <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                 <Ruler className="h-3 w-3" />
                 <span className="text-xs">Frontage</span>
               </div>
               <span className="text-lg font-bold text-gray-900">
                 {propertyData.lotDimensions.frontage.toFixed(1)}
               </span>
               <span className="text-xs text-gray-500 ml-1">m</span>
             </div>
             <div className="bg-white rounded p-2 text-center border border-amber-100">
               <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
                 <Ruler className="h-3 w-3 rotate-90" />
                 <span className="text-xs">Depth</span>
               </div>
               <span className="text-lg font-bold text-gray-900">
                 {propertyData.lotDimensions.depth.toFixed(1)}
               </span>
               <span className="text-xs text-gray-500 ml-1">m</span>
             </div>
           </div>
           {propertyData.lotDimensions.confidence < 0.8 && (
             <p className="text-xs text-amber-700 mt-2 italic">
               Note: Irregular lot shape - dimensions are estimates
             </p>
           )}
         </div>
       )}

       {expectedLayers.map((layerName) => {
         const layer = layerMap.get(layerName)
         const isPresent = !!layer

         // Determine color scheme based on layer type
         const isSEPP = layerName === 'Special Provisions'

         // Display name mapping
         const displayName = isSEPP ? 'SEPP Requirements' : layerName

         // Color scheme: SEPP/Special Provisions=Purple (matches "Applied from NSW Planning Portal"), LEP=Teal, N/A=Gray
         const colors = isPresent
           ? (isSEPP
             ? { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-800', circleBg: 'bg-purple-100', circleText: 'text-purple-700', circleBorder: 'border-purple-300', circleActiveBg: 'bg-purple-600' }
             : { bg: 'bg-white', border: 'border-gray-200', text: 'text-teal-700', circleBg: 'bg-teal-50', circleText: 'text-teal-700', circleBorder: 'border-teal-200', circleActiveBg: 'bg-teal-600' })
           : { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', circleBg: '', circleText: '', circleBorder: '', circleActiveBg: '' }

         return (
           <div key={layerName} className={`border rounded-lg ${colors.bg} ${colors.border}`}>
             <Button
               variant="ghost"
               className="!flex w-full justify-between h-auto p-2 font-normal whitespace-normal text-left hover:opacity-90"
               style={isPresent && isSEPP ? { backgroundColor: 'rgb(250 245 255)', backgroundImage: 'none' } as React.CSSProperties : {}}
               onClick={() => layer && toggleLayer(layer.id)}
               disabled={!isPresent}
             >
               <div className="flex items-start justify-between gap-2 w-full">
                 <span className={`font-medium text-xs leading-tight flex-1 break-words ${colors.text}`}>{displayName}</span>
                 {isPresent ? (
                   <div className={`flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold flex-shrink-0 ${expandedLayers.has(layer.id) ? `${colors.circleActiveBg} text-white` : `${colors.circleBg} ${colors.circleText} border ${colors.circleBorder}`}`}>
                     {layer.results.length}
                   </div>
                 ) : (
                   <span className="text-xs text-gray-500 flex-shrink-0">N/A</span>
                 )}
               </div>
             </Button>

             {layer && expandedLayers.has(layer.id) && (
               <div className={`border-t p-2 space-y-2 ${isSEPP ? 'bg-purple-50' : 'bg-gray-50'}`}>
                 {layer.results.map((result, idx) => {
                   // For Special Provisions (SEPP), add matching labels from "Applied from NSW Planning Portal"
                   const mapType = result['Map Type'];
                   const classValue = result['Class'];
                   const label = result['Label'];

                   // Determine SEPP provision type for matching labels - purple shades for cohesion
                   const getSeppLabel = () => {
                     if (mapType === 'WAT') return { emoji: '💧', label: 'Water Target', color: 'bg-purple-100 text-purple-900 border-l-4 border-purple-400' };
                     if (mapType === 'CLM') return { emoji: '🌡️', label: 'Climate Zone', color: 'bg-purple-100 text-purple-900 border-l-4 border-purple-500' };
                     if (mapType === 'BAL') return { emoji: '🏠', label: 'BASIX', color: 'bg-purple-100 text-purple-900 border-l-4 border-purple-600' };
                     if (mapType === 'TEW') return { emoji: '🔥', label: 'Thermal Energy', color: 'bg-purple-100 text-purple-900 border-l-4 border-purple-700' };
                     return null;
                   };
                   const seppLabel = isSEPP ? getSeppLabel() : null;

                   return (
                   <div key={idx} className="bg-white rounded-lg p-2 shadow-sm overflow-hidden">
                     {/* SEPP Special Provisions: Show matching colored label */}
                     {seppLabel && (
                       <div className="mb-2">
                         <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded ${seppLabel.color}`}>
                           {seppLabel.emoji} {seppLabel.label}: <span className="font-bold">{classValue}{label ? ` (${label})` : ''}</span>
                         </span>
                       </div>
                     )}

                     {/* Top row: Blue and Green pills stacked in top right corner */}
                     <div className="mb-2">
                       <div className="flex flex-col gap-1">
                         {result['EPI Name'] && (
                           <Badge className="text-xs px-2 py-1 bg-sky-100 text-sky-800 whitespace-normal leading-tight break-words">
                             {result['EPI Name']}{result['Legislative Clause'] ? ` - ${result['Legislative Clause']}` : ''}
                           </Badge>
                         )}
                         {result['Amendment'] && (
                           <Badge className="text-xs px-2 py-0.5 bg-green-100 text-green-800">
                             {result['Amendment']}
                           </Badge>
                         )}
                       </div>
                     </div>

                     {/* Main content - important fields as text lines */}
                     <div className="space-y-1 text-sm">
                       {result['Maximum Building Height'] && (
                         <p>
                           <span className="text-gray-700">Maximum Height of Buildings:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Maximum Building Height']}{result['Units'] || 'm'}</span>
                         </p>
                       )}
                       {result['Floor Space Ratio'] && (
                         <p>
                           <span className="text-gray-700">Floor Space Ratio:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Floor Space Ratio']}:1 sq metres</span>
                         </p>
                       )}
                       {result['Zone'] && (
                         <p>
                           <span className="text-gray-700">Zone:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Zone']}</span>
                         </p>
                       )}
                       {result['Land Use'] && (
                         <p>
                           <span className="text-gray-700">Land Use:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Land Use']}</span>
                         </p>
                       )}
                       {!seppLabel && result['Class'] && (
                         <p>
                           <span className="text-gray-700">Class:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Class']}</span>
                         </p>
                       )}
                       {result['Canopy %'] && (
                         <p>
                           <span className="text-gray-700">Canopy Coverage:</span>{' '}
                           <span className="font-semibold text-gray-900">{result['Canopy %']}%</span>
                         </p>
                       )}
                     </div>

                     {/* All other metadata - simple list format */}
                     <div className="space-y-0.5 text-xs mt-2 pt-2 border-t">
                       {getSecondaryFields(result).filter(([key]) =>
                         key !== 'Amendment' &&
                         key !== 'EPI Name' &&
                         key !== 'Legislative Clause' &&
                         key !== 'Maximum Building Height' &&
                         key !== 'Units' &&
                         key !== 'Floor Space Ratio' &&
                         key !== 'Zone' &&
                         key !== 'Land Use' &&
                         key !== 'Class' &&
                         key !== 'Canopy %'
                       ).map(([key, value]) => (
                         <div key={key} className="leading-relaxed">
                           <span className="text-gray-500 font-medium">{key}:</span>{' '}
                           <span className="text-gray-900 font-semibold">
                             {typeof formatValue(key, value) === 'object' ? formatValue(key, value) : formatValue(key, value)}
                           </span>
                         </div>
                       ))}
                     </div>

                    {/* Inline contextual link based on keywords */}
                    {(layerName.toLowerCase().includes('acid') || 
                      layerName.toLowerCase().includes('sulfate') || 
                      layerName.toLowerCase().includes('contamination') ||
                      result['Class']?.toLowerCase().includes('acid') ||
                      JSON.stringify(result).toLowerCase().includes('acid sulfate')) && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <a
                          href="https://www.planning.nsw.gov.au/policy-and-legislation/environment/acid-sulfate-soils"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-xs text-teal-700 hover:text-teal-900 hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Check Acid Sulfate Soils Map
                        </a>
                      </div>
                    )}
                   </div>
                   );
                 })}
               </div>
             )}
           </div>
         )
       })}
     </CardContent>
     )}
   </Card>
 )
}
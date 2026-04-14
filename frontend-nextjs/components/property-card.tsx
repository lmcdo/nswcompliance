"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MapPin, Home, Layers, Ruler, Building, DollarSign, BarChart3, Shield, AlertTriangle, Leaf, Plane, CheckCircle2, XCircle, HelpCircle } from "lucide-react"
import { useCdcEligibility } from "@/hooks/useCdcEligibility"

interface PropertyData {
 propId?: number
 address: string
 zone?: string
 lga?: string
 area?: string
 lot?: string
 dpNumber?: string
 landValue?: string
 maxHeight?: number
 maxFsr?: number
 minLotSize?: number
 heritage?: {
   isHeritage: boolean
   heritageType?: string
   heritageClause?: string
 }
 environmental?: {
   acidSulfateSoils?: string
   basixClimate?: string
   basixWater?: string
   floodProne: boolean
   bushfireProne: boolean
 }
 anef?: {
   inAnefZone: boolean
   anefLevel: number | null
   airport: {
     code: string
     name: string
     version: string
   } | null
   buildingAcceptability: Array<{
     buildingType: string
     displayName: string
     status: 'acceptable' | 'conditional' | 'unacceptable'
   }> | null
 }
 seppOverlays?: Array<{
   seppName: string
   mapType: string
   value: string
   type: string
 }>
}

export function PropertyCard() {
 const [address, setAddress] = useState("")
 const [property, setProperty] = useState<PropertyData>({
   address: "",
   environmental: {
     floodProne: false,
     bushfireProne: false
   },
   seppOverlays: []
 })
 const [isLoading, setIsLoading] = useState(false)

 // CDC eligibility check
 // eslint-disable-next-line @typescript-eslint/no-explicit-any
 const { checkEligibility, result: cdcResult, isLoading: cdcLoading } = useCdcEligibility as any

 const fetchPropertyData = async (addr: string) => {
   if (!addr) return

   setIsLoading(true)
   try {
     const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
     if (response.ok) {
       const apiResponse = await response.json()
       const data = apiResponse.data

       // Map API response to PropertyCard format - EXTRACT ALL DATA FROM REAL API
       console.log('🔍 RAW API DATA:', data)
       console.log('🔍 Planning Layers:', data.planningLayers)
       console.log('🔍 Constraints:', data.constraints)

       // Extract SEPP overlays from Special Provisions layer
       const specialProvisions = data.planningLayers?.find((layer: any) =>
         layer.layerName === 'Special Provisions'
       )
       const seppOverlays = specialProvisions?.results?.map((result: any) => ({
         seppName: result['EPI Name'] || result.title || 'Unknown SEPP',
         mapType: result['Map Type'] || '',
         value: result['Class'] || result['Type'] || '',
         type: result['Type'] || ''
       })) || []

       // Check for heritage in layers
       const heritageLayer = data.planningLayers?.find((layer: any) =>
         layer.layerName === 'Heritage Map' || layer.layerName.includes('Heritage')
       )
       const hasHeritage = !!heritageLayer?.results?.length || data.constraints?.heritage || data.heritage?.isHeritage

       const mappedData = {
         propId: data.propId,
         address: data.address,
         area: data.propertyArea,
         zone: data.constraints?.zone,
         lga: data.constraints?.lga,
         landValue: data.landValue,
         maxHeight: data.constraints?.maxHeight,
         maxFsr: data.constraints?.maxFsr,
         minLotSize: data.constraints?.minLotSize,
         lot: data.lotDetails?.lot || data.lot,
         dpNumber: data.lotDetails?.dpNumber || data.dpNumber,
         heritage: {
           isHeritage: hasHeritage,
           heritageType: data.heritage?.heritageType || data.constraints?.heritageType || (hasHeritage ? 'Heritage Conservation Area' : undefined),
           heritageClause: heritageLayer?.results?.[0]?.['Legislative Clause'] || data.heritage?.heritageClause
         },
         environmental: {
           acidSulfateSoils: data.constraints?.acidSulfateSoils || data.environmental?.acidSulfateSoils,
           basixClimate: data.constraints?.basixClimate || data.environmental?.basixClimate,
           basixWater: data.constraints?.basixWater || data.environmental?.basixWater,
           floodProne: data.constraints?.floodProne || data.environmental?.floodProne || false,
           bushfireProne: data.constraints?.bushfireProne || data.environmental?.bushfireProne || false
         },
         anef: data.anefData ? {
           inAnefZone: data.anefData.inAnefZone,
           anefLevel: data.anefData.anefLevel,
           airport: data.anefData.airport,
           buildingAcceptability: data.anefData.buildingAcceptability
         } : undefined,
         seppOverlays: seppOverlays
       }

       setProperty(prev => ({ ...prev, ...mappedData }))
       console.log('PropertyCard updated with ALL data:', mappedData)

       // Trigger CDC eligibility check
       if (mappedData.address) {
         checkEligibility(mappedData.address)
       }
     }
   } catch (error) {
     console.error('Failed to fetch property data:', error)
   }
   setIsLoading(false)
 }

 useEffect(() => {
   if (address) {
     fetchPropertyData(address)
   }
 }, [address])

 // Listen for address selection from header
 useEffect(() => {
   const handleAddressSelected = (event: CustomEvent) => {
     const newAddress = event.detail
     console.log('PropertyCard received address event:', newAddress)
     setAddress(newAddress)
     fetchPropertyData(newAddress)
   }

   // Listen on both window and document for compatibility
   window.addEventListener('addressSelected', handleAddressSelected as EventListener)
   document.addEventListener('addressSelected', handleAddressSelected as EventListener)
   return () => {
     window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
     document.removeEventListener('addressSelected', handleAddressSelected as EventListener)
   }
 }, [])

 if (isLoading) {
   return (
     <Card>
       <CardContent className="p-6">
         <div className="animate-pulse space-y-4">
           <div className="h-4 bg-gray-200 rounded w-3/4"></div>
           <div className="h-4 bg-gray-200 rounded w-1/2"></div>
           <div className="h-4 bg-gray-200 rounded w-2/3"></div>
         </div>
       </CardContent>
     </Card>
   )
 }

 return (
   <div className="space-y-4">
     {/* Property Address */}
     {property.address && (
       <Card>
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg">
             <Home className="h-5 w-5" />
             Property Address
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           <div className="text-sm">
             <span className="text-gray-600">Address:</span>
             <div className="font-medium">{property.address}</div>
           </div>
           {property.propId && (
             <div className="text-sm">
               <span className="text-gray-600">Property ID:</span>
               <div className="font-medium">#{property.propId}</div>
             </div>
           )}
           {property.lot && (
             <div className="text-sm">
               <span className="text-gray-600">Lot:</span>
               <div className="font-medium">{property.lot}</div>
             </div>
           )}
           {property.dpNumber && (
             <div className="text-sm">
               <span className="text-gray-600">DP Number:</span>
               <div className="font-medium">{property.dpNumber}</div>
             </div>
           )}
         </CardContent>
       </Card>
     )}

     {/* Basic Property Info */}
     {property.zone && (
       <Card>
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg">
             <Layers className="h-5 w-5" />
             Basic Information
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           <div className="grid grid-cols-2 gap-4 text-sm">
             <div>
               <span className="text-gray-600">Zone:</span>
               <div className="font-medium">{property.zone}</div>
             </div>
             <div>
               <span className="text-gray-600">LGA:</span>
               <div className="font-medium">{property.lga}</div>
             </div>
             <div>
               <span className="text-gray-600">Area:</span>
               <div className="font-medium">{property.area}</div>
             </div>
             <div>
               <span className="text-gray-600">Land Value:</span>
               <div className="font-medium">{property.landValue}</div>
             </div>
           </div>
         </CardContent>
       </Card>
     )}

     {/* Development Standards */}
     {(property.maxHeight || property.maxFsr || property.minLotSize) && (
       <Card>
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg">
             <Building className="h-5 w-5" />
             Development Standards
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           {property.maxHeight && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">Max Height:</span>
               <Badge variant="outline">{property.maxHeight}m</Badge>
             </div>
           )}
           {property.maxFsr && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">Max FSR:</span>
               <Badge variant="outline">{property.maxFsr}:1</Badge>
             </div>
           )}
           {property.minLotSize && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">Min Lot Size:</span>
               <Badge variant="outline">{property.minLotSize}m²</Badge>
             </div>
           )}
         </CardContent>
       </Card>
     )}

     {/* CDC Eligibility Indicator */}
     {property.address && (
       <Card className={
         cdcResult?.eligible === 'no' ? 'border-red-200 bg-red-50' :
         cdcResult?.eligible === 'yes' ? 'border-green-200 bg-green-50' :
         'border-amber-200 bg-amber-50'
       }>
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg">
             {cdcLoading ? (
               <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
             ) : cdcResult?.eligible === 'no' ? (
               <XCircle className="h-5 w-5 text-red-600" />
             ) : cdcResult?.eligible === 'yes' ? (
               <CheckCircle2 className="h-5 w-5 text-green-600" />
             ) : (
               <HelpCircle className="h-5 w-5 text-amber-600" />
             )}
             <span className={
               cdcResult?.eligible === 'no' ? 'text-red-800' :
               cdcResult?.eligible === 'yes' ? 'text-green-800' :
               'text-amber-800'
             }>
               CDC Pathway
             </span>
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           {cdcLoading ? (
             <div className="text-sm text-gray-600">Checking eligibility...</div>
           ) : cdcResult ? (
             <>
               <div className="flex items-center gap-2">
                 <Badge variant="outline" className={
                   cdcResult.eligible === 'no' ? 'bg-red-100 text-red-800' :
                   cdcResult.eligible === 'yes' ? 'bg-green-100 text-green-800' :
                   'bg-amber-100 text-amber-800'
                 }>
                   {cdcResult.eligible === 'no' ? 'CDC Excluded' :
                    cdcResult.eligible === 'yes' ? 'CDC Likely Available' :
                    'Verification Required'}
                 </Badge>
               </div>

               {/* Show exclusion reasons */}
               {cdcResult.exclusions && cdcResult.exclusions.length > 0 && (
                 <div className="space-y-1">
                   <div className="text-xs text-gray-600 font-medium">Exclusion reasons:</div>
                   {cdcResult.exclusions.map((exc: any, i: number) => (
                     <div key={i} className="flex items-start gap-2 text-sm">
                       <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                       <span className="text-red-700">{exc.reason}</span>
                     </div>
                   ))}
                 </div>
               )}

               {/* Show checks performed */}
               {cdcResult.checksPerformed && cdcResult.checksPerformed.length > 0 && cdcResult.eligible !== 'no' && (
                 <div className="text-xs text-gray-500">
                   Checked: {cdcResult.checksPerformed.slice(0, 4).join(', ')}
                   {cdcResult.checksPerformed.length > 4 && ` +${cdcResult.checksPerformed.length - 4} more`}
                 </div>
               )}

               <div className="text-xs text-gray-500 italic pt-2 border-t">
                 {cdcResult.disclaimer?.slice(0, 100) || 'Preliminary indicator only. Verify with a registered certifier.'}
               </div>
             </>
           ) : (
             <div className="text-sm text-gray-500">Enter an address to check CDC eligibility</div>
           )}
         </CardContent>
       </Card>
     )}

     {/* Environmental Constraints */}
     {(property.environmental?.acidSulfateSoils || property.environmental?.basixClimate || property.environmental?.basixWater || property.environmental?.floodProne || property.environmental?.bushfireProne) && (
       <Card className="border-green-200 bg-green-50">
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg text-green-800">
             <Leaf className="h-5 w-5" />
             Environmental
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           {property.environmental?.acidSulfateSoils && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">Acid Sulfate Soils:</span>
               <Badge variant="outline" className="bg-green-100 text-green-800">
                 {property.environmental?.acidSulfateSoils}
               </Badge>
             </div>
           )}
           {property.environmental?.basixClimate && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">BASIX Climate:</span>
               <Badge variant="outline" className="bg-green-100 text-green-800">
                 Zone {property.environmental?.basixClimate}
               </Badge>
             </div>
           )}
           {property.environmental?.basixWater && (
             <div className="flex justify-between items-center">
               <span className="text-gray-600">BASIX Water:</span>
               <Badge variant="outline" className="bg-green-100 text-green-800">
                 {property.environmental?.basixWater}
               </Badge>
             </div>
           )}
           {property.environmental?.floodProne && (
             <div className="flex items-center gap-2 text-sm">
               <AlertTriangle className="h-4 w-4 text-amber-600" />
               <span className="text-amber-800 font-medium">Flood Prone Area</span>
             </div>
           )}
           {property.environmental?.bushfireProne && (
             <div className="flex items-center gap-2 text-sm">
               <AlertTriangle className="h-4 w-4 text-red-600" />
               <span className="text-red-800 font-medium">Bushfire Prone Area</span>
             </div>
           )}
         </CardContent>
       </Card>
     )}

     {/* Aircraft Noise (ANEF) */}
     {property.anef?.inAnefZone && (
       <Card className="border-orange-200 bg-orange-50">
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg text-orange-800">
             <Plane className="h-5 w-5" />
             Aircraft Noise Zone
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           <div className="flex justify-between items-center">
             <span className="text-gray-600">ANEF Level:</span>
             <Badge variant="outline" className="bg-orange-100 text-orange-800 font-bold">
               {property.anef.anefLevel} ANEF
             </Badge>
           </div>
           {property.anef.airport && (
             <div className="text-sm">
               <span className="text-gray-600">Airport:</span>
               <div className="font-medium">{property.anef.airport.name} ({property.anef.airport.code})</div>
               <div className="text-xs text-gray-500">{property.anef.airport.version}</div>
             </div>
           )}
           {property.anef.buildingAcceptability && (
             <div className="mt-3 pt-3 border-t border-orange-200">
               <div className="text-xs text-gray-600 mb-2">Building Acceptability (AS2021:2015):</div>
               <div className="space-y-1">
                 {property.anef.buildingAcceptability.slice(0, 4).map((item, index) => (
                   <div key={index} className="flex justify-between items-center text-xs">
                     <span className="text-gray-600 truncate mr-2">{item.displayName}</span>
                     <Badge
                       variant="outline"
                       className={
                         item.status === 'acceptable' ? 'bg-green-100 text-green-800' :
                         item.status === 'conditional' ? 'bg-amber-100 text-amber-800' :
                         'bg-red-100 text-red-800'
                       }
                     >
                       {item.status}
                     </Badge>
                   </div>
                 ))}
               </div>
             </div>
           )}
         </CardContent>
       </Card>
     )}

     {/* SEPP Overlays */}
     {property.seppOverlays && property.seppOverlays.length > 0 && (
       <Card className="border-blue-200 bg-blue-50">
         <CardHeader className="pb-3">
           <CardTitle className="flex items-center gap-2 text-lg text-blue-800">
             <AlertTriangle className="h-5 w-5" />
             State Policies (SEPPs)
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-3">
           {property.seppOverlays?.map((sepp, index) => (
             <div key={index} className="p-3 bg-white rounded-lg border border-blue-200">
               <div className="text-sm">
                 <div className="font-medium text-blue-800">{sepp.seppName}</div>
                 <div className="text-gray-600 mt-1">{sepp.type}: {sepp.value}</div>
                 {sepp.mapType && (
                   <div className="text-xs text-gray-500 mt-1">Map Type: {sepp.mapType}</div>
                 )}
               </div>
             </div>
           ))}
         </CardContent>
       </Card>
     )}

     {/* No Data State */}
     {!property.zone && !isLoading && address && (
       <Card>
         <CardContent className="p-6 text-center text-gray-500">
           <Building className="h-12 w-12 mx-auto mb-4 text-gray-300" />
           <div className="text-lg mb-2">No Property Data Found</div>
           <div className="text-sm">
             Unable to retrieve planning data for this address.
           </div>
         </CardContent>
       </Card>
     )}
   </div>
 )
}
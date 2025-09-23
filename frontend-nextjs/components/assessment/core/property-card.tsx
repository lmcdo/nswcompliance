import { MapPin, History, FileText } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export function PropertyCard() {
 return (
 <Card className="p-6 shadow-sm border border-gray-100 rounded-xl bg-white">
 <div className="space-y-6">
 <div>
 <h3 className="text-xl font-semibold text-gray-900 leading-tight">30 Illawarra Road</h3>
 <p className="text-gray-500 text-sm mt-2">Marrickville NSW 2204</p>
 </div>

 <hr className="border-gray-100" />

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-3">
 <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">Zone</div>
 <Badge className="bg-green-400 text-white hover:bg-green-500 font-medium px-3 py-1.5 rounded-lg">R2</Badge>
 </div>
 <div className="space-y-3">
 <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">Area</div>
 <Badge variant="secondary" className="bg-gray-50 text-gray-700 font-medium px-3 py-1.5 rounded-lg">
 208m²
 </Badge>
 </div>
 <div className="space-y-3">
 <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">LGA</div>
 <Badge variant="outline" className="font-medium px-3 py-1.5 rounded-lg border-gray-200">
 Inner West
 </Badge>
 </div>
 <div className="space-y-3">
 <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">Lot</div>
 <Badge variant="outline" className="font-medium px-3 py-1.5 rounded-lg border-gray-200">
 DP 12345
 </Badge>
 </div>
 </div>

 <div className="flex gap-3 pt-4">
 <Button
 variant="outline"
 size="sm"
 className="flex-1 h-10 text-sm font-medium bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white border-0 rounded-lg"
 >
 <MapPin className="h-4 w-4 mr-2" />
 Map
 </Button>
 <Button
 variant="outline"
 size="sm"
 className="flex-1 h-10 text-sm font-medium bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white border-0 rounded-lg"
 >
 <History className="h-4 w-4 mr-2" />
 History
 </Button>
 <Button
 variant="outline"
 size="sm"
 className="flex-1 h-10 text-sm font-medium bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white border-0 rounded-lg"
 >
 <FileText className="h-4 w-4 mr-2" />
 Documents
 </Button>
 </div>
 </div>
 </Card>
 )
}

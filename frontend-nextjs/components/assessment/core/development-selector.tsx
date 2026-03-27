import { ChevronDown } from "lucide-react"
import { Card } from "@/components/ui/card"

export function DevelopmentSelector(props: Record<string, any> = {}) {
 return (
 <Card className="p-6 shadow-sm">
 <div className="space-y-4">
 <label className="text-sm font-semibold text-gray-700">Development Type:</label>
 <div className="relative">
 <select className="w-full p-3 border border-gray-300 rounded-md bg-white text-base appearance-none pr-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-medium">
 <option>Dual Occupancy</option>
 <option>Single Dwelling</option>
 <option>Multi Dwelling Housing</option>
 <option>Subdivision</option>
 <option>Commercial Development</option>
 <option>Industrial Development</option>
 </select>
 <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
 </div>
 </div>
 </Card>
 )
}

import { Search } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export function QuickSearch() {
 const suggestions = ["Minimum lot size R2", "Height limits", "Setback requirements"]

 const results = [
 {
 title: "LEP Cl 4.1 - Lot size",
 type: "LEP",
 },
 {
 title: "DCP S3.2 - Subdivision",
 type: "DCP",
 },
 ]

 return (
 <div>
 <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Search</h3>
 <Card className="p-5 shadow-sm">
 <div className="space-y-5">
 <div>
 <label className="text-sm font-semibold text-gray-700 block mb-3">Search Provisions</label>
 <div className="relative">
 <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
 <Input placeholder="Search..." className="pl-10 h-10 text-sm focus:ring-2 focus:ring-blue-500" />
 </div>
 </div>

 <div>
 <div className="text-sm font-medium text-gray-600 mb-3">Recent/Suggested:</div>
 <ul className="space-y-2">
 {suggestions.map((suggestion, index) => (
 <li
 key={index}
 className="text-sm text-blue-600 hover:text-blue-800 cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors"
 >
 • {suggestion}
 </li>
 ))}
 </ul>
 </div>

 <div>
 <div className="text-sm font-medium text-gray-600 mb-3">Results</div>
 <div className="max-h-48 overflow-y-auto space-y-3">
 {results.map((result, index) => (
 <div
 key={index}
 className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
 >
 <div className="text-sm font-semibold text-gray-900 mb-3">{result.title}</div>
 <div className="flex gap-2">
 <Button
 size="sm"
 className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white text-xs font-medium px-3"
 >
 Apply
 </Button>
 <Button
 size="sm"
 className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white text-xs font-medium px-3"
 >
 View Full
 </Button>
 </div>
 </div>
 ))}
 </div>
 </div>
 </div>
 </Card>
 </div>
 )
}

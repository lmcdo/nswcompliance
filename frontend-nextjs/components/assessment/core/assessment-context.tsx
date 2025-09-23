import { Calendar, AlertTriangle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export function AssessmentContext() {
 return (
 <div>
 <h3 className="text-lg font-semibold text-gray-900 mb-4">Assessment Context</h3>
 <Card className="p-5 border-amber-200 shadow-sm">
 <div className="space-y-5">
 <div>
 <label className="text-sm font-semibold text-gray-700 block mb-3">Assessment Date</label>
 <div className="relative">
 <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
 <Input type="date" defaultValue="2025-09-21" className="pl-10 h-10 text-sm font-medium" />
 </div>
 </div>

 <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
 <div className="flex items-start gap-3">
 <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
 <div className="text-sm">
 <div className="font-semibold text-amber-800 mb-1">Version Alert</div>
 <div className="text-amber-700 leading-relaxed">
 LEP updated 3 days ago
 <br />
 Using version 1.3
 </div>
 <Button
 variant="link"
 className="h-auto p-0 text-amber-700 text-sm mt-2 font-medium hover:text-amber-800"
 >
 View Changes
 </Button>
 </div>
 </div>
 </div>
 </div>
 </Card>
 </div>
 )
}

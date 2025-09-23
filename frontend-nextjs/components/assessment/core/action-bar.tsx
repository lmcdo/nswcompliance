import { Button } from "@/components/ui/button"

export function ActionBar() {
 return (
 <div className="h-16 md:h-20 bg-white border-t border-gray-200 px-4 md:px-6 flex items-center justify-between">
 <Button
 variant="ghost"
 className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white text-sm md:text-base"
 >
 Save Draft
 </Button>
 <div className="flex gap-2 md:gap-3">
 <Button className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white text-sm md:text-base px-3 md:px-4">
 Generate Report
 </Button>
 <Button className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white text-sm md:text-base px-3 md:px-4">
 Submit Assessment
 </Button>
 </div>
 </div>
 )
}

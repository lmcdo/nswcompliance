import { Button } from "@/components/ui/button"

export function ActionBar() {
 return (
 <div className="w-full h-16 md:h-20 bg-white border-t border-gray-200 px-4 md:px-6 flex items-center justify-between">
 <Button className="bg-gradient-to-b from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white font-medium text-sm md:text-base px-4 md:px-6 shadow-lg flex-shrink-0">
 Save Draft
 </Button>
 <div className="flex gap-2 md:gap-3 flex-shrink-0">
 <Button className="bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 text-white font-medium text-sm md:text-base px-4 md:px-6 shadow-lg">
 Generate Report
 </Button>
 <Button className="bg-gradient-to-b from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white font-medium text-sm md:text-base px-4 md:px-6 shadow-lg">
 Submit Assessment
 </Button>
 </div>
 </div>
 )
}

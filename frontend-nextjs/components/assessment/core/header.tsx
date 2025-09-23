import { Search, Settings, User, Menu, CheckCircle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export function Header() {
 return (
 <header className="fixed top-0 left-0 right-0 z-50 h-[80px] bg-white border-b border-gray-100 flex items-center px-6 shadow-sm">
 <div className="flex items-center gap-4">
 <Button
 variant="ghost"
 size="sm"
 className="md:hidden bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white"
 >
 <Menu className="h-5 w-5" />
 </Button>
 <div className="flex items-center gap-3">
 <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
 <CheckCircle className="h-5 w-5 text-white" />
 </div>
 <div className="font-semibold text-xl text-gray-900">NSW Planning</div>
 </div>
 </div>

 <div className="flex-1 max-w-md mx-8">
 <div className="relative">
 <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
 <Input
 placeholder="Search address or property..."
 className="pl-10 bg-gray-50 border-gray-200 text-gray-900 placeholder:text-gray-500 focus:bg-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 h-10 rounded-lg"
 />
 </div>
 </div>

 <div className="flex items-center gap-4">
 <div className="hidden sm:flex items-center gap-3">
 <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
 <User className="h-4 w-4 text-emerald-600" />
 </div>
 <div className="text-right">
 <div className="text-sm font-medium text-gray-900">Sarah Peterson</div>
 <div className="text-xs text-gray-500">sarah.p@council.nsw.gov.au</div>
 </div>
 </div>
 <Button
 variant="ghost"
 size="sm"
 className="bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white"
 >
 <Settings className="h-4 w-4" />
 </Button>
 </div>
 </header>
 )
}

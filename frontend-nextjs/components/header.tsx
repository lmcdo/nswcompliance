"use client"

import { Settings, User, Menu, CheckCircle, Share2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PropertySearch } from "@/components/property/PropertySearch"
import { useState } from "react"

export function Header() {
 const [selectedAddress, setSelectedAddress] = useState<string>("")

 const handleAddressSelect = (address: string) => {
 setSelectedAddress(address)
 // Trigger property search in the main app
 window.dispatchEvent(new CustomEvent('addressSelected', { detail: address }))
 }

 return (
 <header style={{
 position: 'fixed',
 top: 0,
 left: 0,
 right: 0,
 width: '100vw',
 height: '80px',
 backgroundColor: 'white',
 borderBottom: '1px solid #f3f4f6',
 zIndex: 50
 }}>
 <div style={{
 width: '100%',
 height: '100%',
 padding: '0 24px',
 display: 'flex',
 alignItems: 'center'
 }}>
 {/* Logo and brand */}
 <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
 <Button
 variant="ghost"
 size="sm"
 style={{ display: 'none' }}
 >
 <Menu style={{ height: '20px', width: '20px' }} />
 </Button>
 <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
 <div style={{
 width: '32px',
 height: '32px',
 backgroundColor: '#2563eb',
 borderRadius: '8px',
 display: 'flex',
 alignItems: 'center',
 justifyContent: 'center'
 }}>
 <CheckCircle style={{ height: '20px', width: '20px', color: 'white' }} />
 </div>
 <div style={{ fontWeight: '600', fontSize: '20px', color: '#111827' }}>NSW Planning</div>
 </div>
 </div>

 {/* Search bar - starts after NSW Planning with space */}
 <div style={{ marginLeft: '32px', flex: 1, maxWidth: '672px' }}>
 <PropertySearch
 onAddressSelect={(address, coordinates) => {
 console.log('Header: Address selected:', address, coordinates)
 setSelectedAddress(address)
 // Trigger property search in the main app
 window.dispatchEvent(new CustomEvent('addressSelected', { detail: address }))
 }}
 loading={false}
 selectedAddress={selectedAddress}
 />
 </div>

 {/* User profile and settings - pushed to far right */}
 <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginLeft: 'auto' }}>
 {/* Share Report button - Coming Soon */}
 <div style={{ position: 'relative' }}>
 <Button
 variant="outline"
 size="sm"
 disabled
 style={{
 height: '36px',
 borderRadius: '6px',
 padding: '6px 12px',
 opacity: 0.6,
 cursor: 'not-allowed',
 display: 'flex',
 alignItems: 'center',
 gap: '6px'
 }}
 >
 <Share2 style={{ height: '16px', width: '16px' }} />
 Share Report
 </Button>
 <span style={{
 position: 'absolute',
 top: '-8px',
 right: '-8px',
 backgroundColor: '#14b8a6',
 color: 'white',
 fontSize: '10px',
 fontWeight: '500',
 padding: '2px 6px',
 borderRadius: '9999px',
 whiteSpace: 'nowrap'
 }}>
 Coming Soon
 </span>
 </div>
 <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
 <div style={{
 width: '32px',
 height: '32px',
 backgroundColor: '#dbeafe',
 borderRadius: '50%',
 display: 'flex',
 alignItems: 'center',
 justifyContent: 'center'
 }}>
 <User style={{ height: '16px', width: '16px', color: '#2563eb' }} />
 </div>
 <div style={{ textAlign: 'right' }}>
 <div style={{ fontSize: '14px', fontWeight: '500', color: '#111827' }}>Sarah Peterson</div>
 <div style={{ fontSize: '12px', color: '#6b7280' }}>sarah.p@council.nsw.gov.au</div>
 </div>
 </div>
 <Button
 variant="ghost"
 size="sm"
 style={{
 backgroundColor: '#2563eb',
 color: 'white',
 height: '32px',
 borderRadius: '6px',
 padding: '6px 12px'
 }}
 >
 <Settings style={{ height: '16px', width: '16px' }} />
 </Button>
 </div>
 </div>
 </header>
 )
}
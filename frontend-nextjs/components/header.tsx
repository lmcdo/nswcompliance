"use client"

import { Settings, User, Menu, CheckCircle } from "lucide-react"
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
 backgroundColor: '#020617',
 borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
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
 <div style={{ fontWeight: '700', fontSize: '16px', color: 'white', letterSpacing: '-0.025em' }}>
 Plot<span style={{ color: '#2dd4bf' }}>Detect</span>
 </div>
 <div style={{ fontWeight: '600', fontSize: '18px', color: 'white' }}>NSW Planning</div>
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
 <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
 <div style={{
 width: '32px',
 height: '32px',
 backgroundColor: 'rgba(45, 212, 191, 0.1)',
 borderRadius: '50%',
 display: 'flex',
 alignItems: 'center',
 justifyContent: 'center'
 }}>
 <User style={{ height: '16px', width: '16px', color: '#2dd4bf' }} />
 </div>
 <div style={{ textAlign: 'right' }}>
 <div style={{ fontSize: '14px', fontWeight: '500', color: 'white' }}>Sarah Peterson</div>
 <div style={{ fontSize: '12px', color: '#64748b' }}>sarah.p@council.nsw.gov.au</div>
 </div>
 </div>
 <Button
 variant="ghost"
 size="sm"
 style={{
 backgroundColor: '#0d9488',
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

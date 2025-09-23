// components/property/PropertySearchSimple.tsx
'use client';

import { useState } from 'react';

export function PropertySearchSimple({ onAddressSelect }: { onAddressSelect: (address: string) => void }) {
 const [value, setValue] = useState('');

 return (
 <div style={{ padding: '20px', background: 'white', borderRadius: '8px' }}>
 <h2>Test Input Field</h2>
 <form onSubmit={(e) => {
 e.preventDefault();
 if (value) onAddressSelect(value);
 }}>
 <input
 type="text"
 value={value}
 onChange={(e) => setValue(e.target.value)}
 placeholder="Type your address here..."
 style={{
 width: '100%',
 padding: '10px',
 fontSize: '16px',
 border: '1px solid #ccc',
 borderRadius: '4px'
 }}
 />
 <button 
 type="submit"
 style={{
 marginTop: '10px',
 padding: '10px 20px',
 background: '#007bff',
 color: 'white',
 border: 'none',
 borderRadius: '4px',
 cursor: 'pointer'
 }}
 >
 Analyze
 </button>
 </form>
 <p>Current value: {value}</p>
 </div>
 );
}
'use client';

import React from 'react';

interface ChecklistItem {
 id: string;
 provision: string;
 clause: string;
 status: 'compliant' | 'non-compliant' | 'pending';
 details?: string;
}

interface ComplianceChecklistProps {
 items?: ChecklistItem[];
}

export default function ComplianceChecklist({ items = [] }: ComplianceChecklistProps) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Compliance Checklist</h3>

 {items.length === 0 ? (
 <p className="text-gray-600">Select a development type to generate checklist</p>
 ) : (
 <div className="space-y-3">
 {items.map((item) => (
 <div key={item.id} className="border rounded p-3">
 <div className="flex items-center justify-between">
 <div>
 <h4 className="font-medium">{item.provision}</h4>
 <p className="text-sm text-gray-600">{item.clause}</p>
 </div>
 <div className={`px-2 py-1 rounded text-xs font-medium ${
 item.status === 'compliant' ? 'bg-green-100 text-green-800' :
 item.status === 'non-compliant' ? 'bg-red-100 text-red-800' :
 'bg-yellow-100 text-yellow-800'
 }`}>
 {item.status}
 </div>
 </div>
 {item.details && (
 <p className="text-sm text-gray-600 mt-2">{item.details}</p>
 )}
 </div>
 ))}
 </div>
 )}
 </div>
 );
}

import React, { useState, useCallback } from 'react';
import type { ComplianceItem } from './types';

interface EvidenceSectionProps {
 items: ComplianceItem[];
 onEvidenceUpdate: (itemId: string, evidence: string[]) => void;
}

interface EvidenceUpload {
 id: string;
 name: string;
 type: string;
 size: number;
 uploadDate: string;
 status: 'uploading' | 'completed' | 'error';
}

export const EvidenceSection: React.FC<EvidenceSectionProps> = ({
 items,
 onEvidenceUpdate
}) => {
 const [selectedItem, setSelectedItem] = useState<string>('');
 const [uploads, setUploads] = useState<EvidenceUpload[]>([]);
 const [dragOver, setDragOver] = useState(false);

 const handleFileSelect = useCallback(async (files: FileList) => {
 const newUploads: EvidenceUpload[] = Array.from(files).map(file => ({
 id: Math.random().toString(36).substr(2, 9),
 name: file.name,
 type: file.type,
 size: file.size,
 uploadDate: new Date().toISOString(),
 status: 'uploading' as const
 }));

 setUploads(prev => [...prev, ...newUploads]);

 // Simulate upload process
 for (const upload of newUploads) {
 try {
 const formData = new FormData();
 const file = Array.from(files).find(f => f.name === upload.name);
 if (file) {
 formData.append('file', file);
 formData.append('itemId', selectedItem);

 const response = await fetch('/api/evidence/upload', {
 method: 'POST',
 body: formData
 });

 if (response.ok) {
 setUploads(prev => prev.map(u =>
 u.id === upload.id ? { ...u, status: 'completed' } : u
 ));

 // Update the item's evidence
 const selectedItemData = items.find(item => item.id === selectedItem);
 if (selectedItemData) {
 const newEvidence = [...(selectedItemData.evidence || []), upload.name];
 onEvidenceUpdate(selectedItem, newEvidence);
 }
 } else {
 throw new Error('Upload failed');
 }
 }
 } catch (error) {
 setUploads(prev => prev.map(u =>
 u.id === upload.id ? { ...u, status: 'error' } : u
 ));
 }
 }
 }, [selectedItem, items, onEvidenceUpdate]);

 const handleDrop = useCallback((e: React.DragEvent) => {
 e.preventDefault();
 setDragOver(false);

 if (e.dataTransfer.files && selectedItem) {
 handleFileSelect(e.dataTransfer.files);
 }
 }, [selectedItem, handleFileSelect]);

 const handleDragOver = useCallback((e: React.DragEvent) => {
 e.preventDefault();
 setDragOver(true);
 }, []);

 const handleDragLeave = useCallback((e: React.DragEvent) => {
 e.preventDefault();
 setDragOver(false);
 }, []);

 const formatFileSize = (bytes: number) => {
 if (bytes === 0) return '0 Bytes';
 const k = 1024;
 const sizes = ['Bytes', 'KB', 'MB', 'GB'];
 const i = Math.floor(Math.log(bytes) / Math.log(k));
 return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
 };

 const getStatusIcon = (status: EvidenceUpload['status']) => {
 switch (status) {
 case 'uploading':
 return (
 <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
 <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
 <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
 </svg>
 );
 case 'completed':
 return (
 <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
 </svg>
 );
 case 'error':
 return (
 <svg className="w-4 h-4 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
 </svg>
 );
 }
 };

 return (
 <div className="bg-white border rounded-lg p-6">
 <h3 className="text-lg font-semibold text-gray-900 mb-4">Evidence Management</h3>

 {/* Item Selector */}
 <div className="mb-4">
 <label className="block text-sm font-medium text-gray-700 mb-2">
 Select Compliance Item
 </label>
 <select
 value={selectedItem}
 onChange={(e) => setSelectedItem(e.target.value)}
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 >
 <option value="">Choose an item...</option>
 {items.map(item => (
 <option key={item.id} value={item.id}>
 {item.title} ({item.status})
 </option>
 ))}
 </select>
 </div>

 {selectedItem && (
 <>
 {/* File Upload Area */}
 <div
 className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
 dragOver
 ? 'border-blue-400 bg-blue-50'
 : 'border-gray-300 hover:border-gray-400'
 }`}
 onDrop={handleDrop}
 onDragOver={handleDragOver}
 onDragLeave={handleDragLeave}
 >
 <div className="space-y-2">
 <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
 <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
 </svg>
 <div className="text-sm text-gray-600">
 <label htmlFor="file-upload" className="cursor-pointer text-blue-600 hover:text-blue-800">
 Upload files
 </label>
 {' '}or drag and drop
 </div>
 <p className="text-xs text-gray-500">
 PDF, DOC, DOCX, JPG, PNG up to 10MB
 </p>
 </div>
 <input
 id="file-upload"
 type="file"
 multiple
 accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
 className="hidden"
 onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
 />
 </div>

 {/* Upload List */}
 {uploads.length > 0 && (
 <div className="mt-4">
 <h4 className="text-sm font-medium text-gray-900 mb-2">Uploaded Files</h4>
 <div className="space-y-2">
 {uploads.map(upload => (
 <div key={upload.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
 <div className="flex items-center space-x-3">
 {getStatusIcon(upload.status)}
 <div>
 <div className="text-sm font-medium text-gray-900">{upload.name}</div>
 <div className="text-xs text-gray-500">
 {formatFileSize(upload.size)} • {new Date(upload.uploadDate).toLocaleDateString()}
 </div>
 </div>
 </div>
 <div className="text-xs text-gray-500">
 {upload.status === 'uploading' && 'Uploading...'}
 {upload.status === 'completed' && 'Complete'}
 {upload.status === 'error' && 'Error'}
 </div>
 </div>
 ))}
 </div>
 </div>
 )}

 {/* Existing Evidence */}
 {selectedItem && (() => {
 const item = items.find(i => i.id === selectedItem);
 return item?.evidence && item.evidence.length > 0 ? (
 <div className="mt-4">
 <h4 className="text-sm font-medium text-gray-900 mb-2">Existing Evidence</h4>
 <div className="space-y-2">
 {item.evidence.map((evidence, index) => (
 <div key={index} className="flex items-center justify-between p-2 bg-emerald-50 rounded">
 <span className="text-sm text-gray-900">{evidence}</span>
 <button className="text-rose-800 hover:text-rose-900 text-xs">
 Remove
 </button>
 </div>
 ))}
 </div>
 </div>
 ) : null;
 })()}
 </>
 )}
 </div>
 );
};
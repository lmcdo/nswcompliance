'use client';

import React, { useState, useEffect } from 'react';
import { PropertyDataService, PropertyData } from '../../../lib/property-data';
import { loadGoogleMapsAPI } from '../../../lib/regulatory-engine/google-maps';
import './enhanced.css';

interface EnhancedComplianceResult {
 rule_id: string;
 requirement_type: string;
 compliant: boolean;
 proposed_value: number;
 required_value: number | [number, number];
 gap: number;
 confidence: 'HIGH' | 'MEDIUM' | 'LOW';
 processing_method: 'semantic' | 'manual' | 'fallback';
 source: {
 document: string;
 section: string;
 clause: string;
 url: string;
 };
 mitigation?: string;
 regulatory_text?: string;
 source_grounding?: {
 extraction_text: string;
 source_section: string;
 semantic_confidence: number;
 };
}

interface ComplianceSummary {
 overall_compliant: boolean;
 total_rules_checked: number;
 non_compliant_rules: number;
 source_authority_summary: {
 semantic_rules: number;
 manual_rules: number;
 high_confidence_rules: number;
 };
 next_steps: string[];
}

export default function EnhancedPropertyPage() {
 const [propertyData, setPropertyData] = useState<PropertyData | null>(null);
 const [formerCouncilArea, setFormerCouncilArea] = useState<string | null>(null);
 const [proposal, setProposal] = useState({
 height: 0,
 fsr: 0,
 rear_setback: 0,
 side_setback: 0,
 front_setback: 0
 });
 const [address, setAddress] = useState('');
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState<string | null>(null);
 const [isMapLoaded, setIsMapLoaded] = useState(false);
 const [results, setResults] = useState<EnhancedComplianceResult[]>([]);
 const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary | null>(null);
 const [useSemanticRules, setUseSemanticRules] = useState(true);
 const [showSourceGrounding, setShowSourceGrounding] = useState(false);
 const [resultsCollapsed, setResultsCollapsed] = useState(false);
 const [expandedResults, setExpandedResults] = useState<{[key: number]: boolean}>({});

 // Load Google Maps API
 useEffect(() => {
 const loadMaps = async () => {
 try {
 await loadGoogleMapsAPI();
 setIsMapLoaded(true);
 } catch (err) {
 console.error('Failed to load Google Maps API:', err);
 }
 };
 loadMaps();
 }, []);

 // Initialize Google Autocomplete
 useEffect(() => {
 console.log('Enhanced page - isMapLoaded:', isMapLoaded, 'window.google:', !!window.google);
 
 if (!isMapLoaded || !window.google) {
 console.log('Google Maps not ready yet (enhanced page)');
 return;
 }
 
 const input = document.getElementById('enhanced-address-input') as HTMLInputElement;
 if (!input) {
 console.log('Input element not found (enhanced page)');
 return;
 }
 
 try {
 console.log('Creating Google Autocomplete instance (enhanced page)...');
 const autocomplete = new window.google.maps.places.Autocomplete(input, {
 types: ['address'],
 componentRestrictions: { country: 'au' },
 fields: ['address_components', 'formatted_address', 'geometry']
 });
 
 autocomplete.addListener('place_changed', () => {
 console.log('Place changed event triggered (enhanced page)');
 const place = autocomplete.getPlace();
 console.log('Selected place (enhanced page):', place);
 if (place.formatted_address) {
 console.log('Setting address to (enhanced page):', place.formatted_address);
 setAddress(place.formatted_address);
 }
 });
 
 console.log('Google Autocomplete initialized for enhanced page');
 } catch (err) {
 console.error('Autocomplete initialization failed (enhanced page):', err);
 }
 }, [isMapLoaded]);

 const fetchPropertyData = async () => {
 if (!address) return;
 
 try {
 setLoading(true);
 setError(null);
 
 const data = await PropertyDataService.getPropertyComplianceData(address);
 setPropertyData(data);
 
 const councilArea = PropertyDataService.determineFormerCouncilArea(data);
 setFormerCouncilArea(councilArea);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to load property data');
 } finally {
 setLoading(false);
 }
 };

 const isFormComplete = () => {
 return proposal.height > 0 && proposal.fsr > 0 && 
 proposal.rear_setback > 0 && proposal.side_setback > 0 && 
 proposal.front_setback > 0;
 };

 const toggleResultExpansion = (index: number) => {
 console.log('Toggling result', index, 'current state:', expandedResults[index]);
 setExpandedResults(prev => {
 const newState = {
 ...prev,
 [index]: !prev[index]
 };
 console.log('New expanded state:', newState);
 return newState;
 });
 };

 const checkEnhancedCompliance = async () => {
 if (!isFormComplete() || !propertyData) return;
 
 try {
 setLoading(true);
 
 const requestData = {
 address,
 propertyData: propertyData,
 proposal: {
 height: proposal.height,
 fsr: proposal.fsr,
 rear_setback: proposal.rear_setback,
 side_setback: proposal.side_setback,
 front_setback: proposal.front_setback
 },
 formerCouncilArea: formerCouncilArea,
 useSemanticRules: useSemanticRules,
 includeSourceGrounding: showSourceGrounding
 };

 const response = await fetch('/api/compliance/check', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(requestData)
 });

 if (!response.ok) {
 throw new Error(`API request failed: ${response.status}`);
 }

 const data = await response.json();
 console.log(' Full API Response:', data);
 console.log(' Results Array:', data.results);
 if (data.results && data.results.length > 0) {
 console.log(' First result source_grounding:', data.results[0]?.source_grounding);
 console.log(' First result regulatory_text:', data.results[0]?.regulatory_text);
 }
 setResults(data.results || []);
 setComplianceSummary(data.compliance_summary || null);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to check compliance');
 } finally {
 setLoading(false);
 }
 };

 if (error) {
 return (
 <div style={{ padding: '40px', textAlign: 'center' }}>
 <h2>Enhanced Development Compliance Checker</h2>
 <div style={{ color: '#ef4444', marginBottom: '20px' }}>{error}</div>
 <button onClick={() => setError(null)}>Try Again</button>
 </div>
 );
 }

 return (
 <div style={{ display: 'flex', gap: '40px', maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
 {/* Left Column - Input Form */}
 <div style={{ flex: '0 0 400px', paddingRight: '20px', minHeight: '100vh', overflow: 'visible' }}>
 <div style={{ marginBottom: '30px' }}>
 <h2>Enhanced Compliance Checker</h2>
 <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
 <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px' }}>
 <input type="checkbox" checked={useSemanticRules} onChange={(e) => setUseSemanticRules(e.target.checked)} />
 Semantic Rules
 </label>
 <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px' }}>
 <input type="checkbox" checked={showSourceGrounding} onChange={(e) => setShowSourceGrounding(e.target.checked)} />
 Source Citations
 </label>
 </div>
 </div>
 
 <div style={{ marginBottom: '30px' }}>
 <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Property Address:</label>
 <div style={{ display: 'flex', gap: '8px' }}>
 <input
 id="enhanced-address-input"
 type="text"
 value={address}
 onChange={(e) => setAddress(e.target.value)}
 placeholder="Start typing an address..."
 style={{ flex: 1, padding: '12px', fontSize: '14px', border: '2px solid #ddd', borderRadius: '6px' }}
 />
 <button 
 onClick={fetchPropertyData}
 disabled={loading || !address.trim()}
 style={{ padding: '12px 20px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
 >
 {loading ? '...' : 'Search'}
 </button>
 </div>
 {isMapLoaded && (
 <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>
 Google Autocomplete enabled - start typing for suggestions
 </div>
 )}
 </div>
 
 {propertyData && (
 <>
 <div style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
 <h3 style={{ margin: '0 0 15px 0', fontSize: '18px', color: '#1e40af' }}>{propertyData.address}</h3>
 <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
 <span style={{ padding: '4px 8px', backgroundColor: '#e0e7ff', color: '#1e40af', borderRadius: '4px', fontSize: '12px' }}>{propertyData.zoneDescription}</span>
 {formerCouncilArea && <span style={{ padding: '4px 8px', backgroundColor: '#dcfce7', color: '#166534', borderRadius: '4px', fontSize: '12px' }}>{formerCouncilArea}</span>}
 <span style={{ padding: '4px 8px', backgroundColor: '#f3f4f6', color: '#374151', borderRadius: '4px', fontSize: '12px' }}>H: {propertyData.constraints.maxHeight}m</span>
 <span style={{ padding: '4px 8px', backgroundColor: '#f3f4f6', color: '#374151', borderRadius: '4px', fontSize: '12px' }}>FSR: {propertyData.constraints.maxFsr}</span>
 </div>
 </div>
 
 <div>
 <h4 style={{ marginBottom: '20px', color: '#374151' }}>Enter Your Proposal</h4>
 <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
 <div style={{ display: 'flex', gap: '12px' }}>
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
 <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>Height (m)</label>
 <input 
 type="number" 
 value={proposal.height || ''} 
 onChange={e => {
 const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
 setProposal({...proposal, height: isNaN(value) ? 0 : value});
 }} 
 placeholder="8.5"
 step="0.1" min="0"
 style={{ width: '80px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px', textAlign: 'center' }}
 />
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
 <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>FSR</label>
 <input 
 type="number" 
 value={proposal.fsr || ''} 
 onChange={e => {
 const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
 setProposal({...proposal, fsr: isNaN(value) ? 0 : value});
 }} 
 placeholder="0.5"
 step="0.01" min="0"
 style={{ width: '80px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px', textAlign: 'center' }}
 />
 </div>
 </div>
 <div style={{ display: 'flex', gap: '12px' }}>
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
 <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>Rear (m)</label>
 <input 
 type="number" 
 value={proposal.rear_setback || ''} 
 onChange={e => {
 const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
 setProposal({...proposal, rear_setback: isNaN(value) ? 0 : value});
 }} 
 placeholder="1.5"
 step="0.1" min="0"
 style={{ width: '80px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px', textAlign: 'center' }}
 />
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
 <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>Side (m)</label>
 <input 
 type="number" 
 value={proposal.side_setback || ''} 
 onChange={e => {
 const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
 setProposal({...proposal, side_setback: isNaN(value) ? 0 : value});
 }} 
 placeholder="2.7"
 step="0.1" min="0"
 style={{ width: '80px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px', textAlign: 'center' }}
 />
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
 <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>Front (m)</label>
 <input 
 type="number" 
 value={proposal.front_setback || ''} 
 onChange={e => {
 const value = e.target.value === '' ? 0 : parseFloat(e.target.value);
 setProposal({...proposal, front_setback: isNaN(value) ? 0 : value});
 }} 
 placeholder="2.4"
 step="0.1" min="0"
 style={{ width: '80px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px', textAlign: 'center' }}
 />
 </div>
 </div>
 </div>
 
 <div style={{ marginTop: '24px' }}>
 <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
 Debug: H={proposal.height} F={proposal.fsr} R={proposal.rear_setback} S={proposal.side_setback} Front={proposal.front_setback} Complete={isFormComplete().toString()}
 </div>
 <button 
 disabled={!isFormComplete() || loading}
 onClick={checkEnhancedCompliance}
 style={{
 width: '100%',
 padding: '14px',
 fontSize: '16px',
 fontWeight: 'bold',
 backgroundColor: (!isFormComplete() || loading) ? '#9ca3af' : '#10b981',
 color: 'white',
 border: '2px solid #000',
 borderRadius: '8px',
 cursor: (!isFormComplete() || loading) ? 'not-allowed' : 'pointer',
 boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
 }}
 >
 {loading ? 'Checking...' : isFormComplete() ? 'Check Compliance' : 'Complete all fields'}
 </button>
 </div>
 </div>
 </>
 )}
 </div>

 {/* Right Column - Results */}
 <div style={{ flex: 1 }}>
 {complianceSummary && (
 <div>
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
 <h3 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
 {complianceSummary.overall_compliant ? ' COMPLIANT' : ' NON-COMPLIANT'}
 </h3>
 <div style={{ textAlign: 'right', fontSize: '14px', color: '#6b7280' }}>
 <div>{complianceSummary.total_rules_checked} rules checked</div>
 <div>{complianceSummary.non_compliant_rules} issues found</div>
 <div>{complianceSummary.source_authority_summary.semantic_rules} semantic rules</div>
 </div>
 </div>
 
 <div style={{ marginTop: '24px', padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
 <h4 style={{ margin: '0 0 16px 0', color: '#374151' }}>Source Authority</h4>
 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', fontSize: '14px' }}>
 <div>
 <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981' }}>{complianceSummary.source_authority_summary.semantic_rules}</div>
 <div style={{ color: '#6b7280' }}>Semantic Rules</div>
 </div>
 <div>
 <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6' }}>{complianceSummary.source_authority_summary.manual_rules}</div>
 <div style={{ color: '#6b7280' }}>Manual Rules</div>
 </div>
 <div>
 <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }}>{complianceSummary.source_authority_summary.high_confidence_rules}</div>
 <div style={{ color: '#6b7280' }}>High Confidence</div>
 </div>
 </div>
 
 {complianceSummary.next_steps.length > 0 && (
 <div style={{ marginTop: '20px' }}>
 <h5 style={{ margin: '0 0 8px 0', color: '#374151' }}>Next Steps</h5>
 <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#6b7280' }}>
 {complianceSummary.next_steps.map((step, index) => (
 <li key={index}>{step}</li>
 ))}
 </ul>
 </div>
 )}
 </div>
 </div>
 )}

 {results.length > 0 && (
 <div style={{ marginTop: '32px' }}>
 <h4 
 onClick={() => setResultsCollapsed(!resultsCollapsed)}
 style={{ 
 cursor: 'pointer', 
 marginBottom: '16px', 
 color: '#374151',
 display: 'flex',
 alignItems: 'center',
 justifyContent: 'space-between'
 }}
 >
 Detailed Rule Analysis ({results.length} rules)
 <span>{resultsCollapsed ? '▼' : '▲'}</span>
 </h4>
 {!resultsCollapsed && (
 <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
 {results.map((result, index) => {
 const isExpanded = expandedResults[index];
 return (
 <div key={index} 
 style={{
 border: `2px solid ${result.compliant ? '#10b981' : '#ef4444'}`,
 borderRadius: '8px',
 backgroundColor: result.compliant ? '#f0fdf4' : '#fef2f2',
 overflow: 'hidden'
 }}>
 {/* Accordion Header */}
 <div 
 onClick={() => toggleResultExpansion(index)}
 style={{
 padding: '16px 20px',
 cursor: 'pointer',
 borderBottom: isExpanded ? `1px solid ${result.compliant ? '#10b981' : '#ef4444'}` : 'none',
 backgroundColor: result.compliant ? '#dcfce7' : '#fee2e2'
 }}
 >
 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
 <div style={{ fontSize: '18px', fontWeight: 'bold', color: result.compliant ? '#059669' : '#dc2626' }}>
 {result.compliant ? '' : ''} {result.requirement_type.replace('_', ' ').toUpperCase()}
 </div>
 <div style={{ fontSize: '14px', color: '#6b7280' }}>
 {result.proposed_value}{result.requirement_type.includes('fsr') ? '' : 'm'} 
 {(() => {
 const isSetback = result.requirement_type.includes('setback');
 if (result.compliant) {
 return isSetback ? ' ≥ ' : ' ≤ ';
 } else {
 return isSetback ? ' < ' : ' > ';
 }
 })()}
 {Array.isArray(result.required_value) ? 
 `${result.required_value[0]}-${result.required_value[1]}` : 
 result.required_value}{result.requirement_type.includes('fsr') ? '' : 'm'}
 </div>
 </div>
 <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
 <span style={{ 
 padding: '2px 8px', 
 borderRadius: '12px', 
 fontSize: '11px', 
 fontWeight: 'bold',
 backgroundColor: result.confidence === 'HIGH' ? '#065f46' : result.confidence === 'MEDIUM' ? '#92400e' : '#dc2626',
 color: 'white'
 }}>
 {result.confidence}
 </span>
 <span style={{ 
 padding: '2px 8px', 
 borderRadius: '12px', 
 fontSize: '11px',
 backgroundColor: result.processing_method === 'semantic' ? '#1e40af' : '#374151',
 color: 'white'
 }}>
 {result.processing_method}
 </span>
 <div style={{ 
 fontSize: '16px', 
 color: '#6b7280',
 transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
 transition: 'transform 0.2s ease'
 }}>
 ▼
 </div>
 </div>
 </div>
 </div>

 {/* Accordion Content */}
 {isExpanded && (
 <div style={{ padding: '20px' }}>
 {/* Regulatory Text */}
 <div style={{ 
 margin: '0 0 16px 0', 
 padding: '16px', 
 backgroundColor: '#f8fafc',
 border: '1px solid #e2e8f0',
 borderRadius: '6px',
 borderLeft: '4px solid #3b82f6'
 }}>
 <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1f2937', fontSize: '14px' }}>
 Regulatory Text
 </div>
 <div style={{ 
 fontStyle: 'italic', 
 color: '#374151', 
 fontSize: '14px', 
 lineHeight: '1.5'
 }}>
 "{result.regulatory_text || 'Real regulatory text not yet available for this rule type.'}"
 </div>
 </div>

 {/* Assessment Details */}
 <div style={{ marginBottom: '16px' }}>
 <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937' }}>
 Assessment Details
 </div>
 <p style={{ margin: '0 0 8px 0', fontSize: '15px' }}>
 <strong>Your proposal:</strong> {result.proposed_value}{result.requirement_type.includes('fsr') ? '' : 'm'} 
 {(() => {
 const isSetback = result.requirement_type.includes('setback');
 if (result.compliant) {
 return isSetback ? ' ≥ ' : ' ≤ ';
 } else {
 return isSetback ? ' < ' : ' > ';
 }
 })()}
 <strong>{Array.isArray(result.required_value) ? 
 `${result.required_value[0]}-${result.required_value[1]}` : 
 result.required_value}{result.requirement_type.includes('fsr') ? '' : 'm'}</strong>
 </p>
 {result.gap !== 0 && (
 <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#6b7280' }}>
 Gap: {Math.abs(result.gap).toFixed(2)}{result.requirement_type.includes('fsr') ? '' : 'm'} 
 {result.compliant ? ' buffer' : ' shortfall'}
 </p>
 )}
 </div>

 {/* Mitigation */}
 {result.mitigation && (
 <div style={{ 
 margin: '0 0 16px 0', 
 padding: '12px', 
 backgroundColor: '#fef3c7', 
 border: '1px solid #f59e0b',
 borderRadius: '6px'
 }}>
 <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#92400e' }}>
 Required Action
 </div>
 <div style={{ fontSize: '14px', color: '#92400e' }}>
 {result.mitigation}
 </div>
 </div>
 )}

 {/* Source Grounding */}
 {showSourceGrounding && result.source_grounding && (
 <div style={{ 
 margin: '0 0 16px 0', 
 padding: '12px', 
 backgroundColor: '#f0f9ff',
 border: '1px solid #0ea5e9',
 borderRadius: '6px'
 }}>
 <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#0ea5e9' }}>
 Source Analysis
 </div>
 <div style={{ fontSize: '13px', color: '#0f172a', marginBottom: '6px' }}>
 <strong>Extracted text:</strong> "{result.source_grounding.extraction_text}"
 </div>
 <div style={{ fontSize: '12px', color: '#6b7280' }}>
 Semantic Confidence: {Math.round(result.source_grounding.semantic_confidence * 100)}%
 </div>
 </div>
 )}

 {/* Regulatory Authority */}
 <div style={{ 
 padding: '16px',
 backgroundColor: '#f8fafc',
 border: '1px solid #e2e8f0',
 borderRadius: '6px'
 }}>
 <div style={{ fontWeight: 'bold', marginBottom: '12px', color: '#1f2937' }}>
 Regulatory Authority
 </div>
 <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px', fontSize: '13px' }}>
 <strong>Document:</strong>
 <span>{result.source.document}</span>
 <strong>Section:</strong>
 <span>{result.source.section}</span>
 <strong>Clause:</strong>
 <span>{result.source.clause || result.rule_id}</span>
 <strong>Authority:</strong>
 <span>{result.processing_method === 'semantic' ? 
 `Inner West Council (former ${formerCouncilArea})` : 
 'NSW Department of Planning and Environment'}</span>
 <strong>Verification:</strong>
 <span>{result.processing_method === 'semantic' ? 
 `Semantic extraction (${result.confidence} confidence)` : 
 'Planning Portal API (Official data)'}</span>
 </div>
 <div style={{ marginTop: '12px' }}>
 <a href={result.source.url} target="_blank" rel="noopener noreferrer" 
 style={{ color: '#2563eb', textDecoration: 'underline', fontSize: '12px' }}>
 View Official Document →
 </a>
 </div>
 </div>
 </div>
 )}
 </div>
 );
 })}
 </div>
 )}
 </div>
 )}
 
 {results.length === 0 && propertyData && (
 <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
 <h3>Ready for Enhanced Compliance Check</h3>
 <p>Complete all fields in the left panel and click "Check Compliance" to see detailed semantic analysis here.</p>
 </div>
 )}
 </div>
 
 <div style={{ 
 position: 'fixed', 
 bottom: '20px', 
 right: '20px', 
 fontSize: '11px', 
 color: '#6b7280',
 backgroundColor: 'white',
 padding: '12px',
 border: '1px solid #e5e7eb',
 borderRadius: '6px',
 maxWidth: '350px',
 boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
 }}>
 <strong>Enhanced Processing:</strong> Uses LangExtract + AutoSchemaKG for semantic rule understanding with source grounding.
 Always verify with current council DCPs before final submission.
 </div>
 </div>
 );
}
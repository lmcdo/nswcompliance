'use client';

import React, { useState, useEffect } from 'react';

// Google Maps API types are declared in google-maps.ts
import { loadGoogleMapsAPI } from '../../lib/regulatory-engine/google-maps';
import { PropertyDataService, PropertyData } from '../../lib/property-data';
import { DeterministicComplianceEngine } from '../../lib/deterministic-compliance';

export default function PropertyPage() {
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
 const [results, setResults] = useState<any[]>([]);
 const [complianceEngine] = useState(() => new DeterministicComplianceEngine());
 
 // Load Google Maps API (optional)
 useEffect(() => {
 const loadMaps = async () => {
 try {
 await loadGoogleMapsAPI();
 setIsMapLoaded(true);
 } catch (err) {
 console.warn('Google Maps not available, using manual address entry:', err);
 // Don't set error - just continue without autocomplete
 setIsMapLoaded(false);
 }
 };
 
 loadMaps();
 }, []);
 
 // Google Autocomplete for address input
 useEffect(() => {
 console.log('Standard page - isMapLoaded:', isMapLoaded, 'window.google:', !!window.google);
 
 if (!isMapLoaded || !window.google) {
 console.log('Google Maps not ready yet (standard page)');
 return;
 }
 
 const input = document.getElementById('address-autocomplete') as HTMLInputElement;
 if (!input) {
 console.log('Input element not found (standard page)');
 return;
 }
 
 try {
 console.log('Creating Google Autocomplete instance (standard page)...');
 const autocomplete = new window.google.maps.places.Autocomplete(input, {
 types: ['address'],
 componentRestrictions: { country: 'au' },
 fields: ['address_components', 'formatted_address', 'geometry']
 });
 
 autocomplete.addListener('place_changed', () => {
 console.log('Place changed event triggered (standard page)');
 const place = autocomplete.getPlace();
 console.log('Selected place (standard page):', place);
 if (place.formatted_address) {
 console.log('Setting address to (standard page):', place.formatted_address);
 setAddress(place.formatted_address);
 }
 });
 
 console.log('Google Autocomplete initialized for standard page');
 } catch (err) {
 console.error('Autocomplete initialization failed (standard page):', err);
 }
 }, [isMapLoaded]);
 
 // Function to fetch property data (called when search button is clicked)
 const fetchPropertyData = async () => {
 if (!address.trim()) return;
 
 try {
 setLoading(true);
 setError(null);
 setPropertyData(null);
 
 // Get property data from NSW Planning Portal
 const data = await PropertyDataService.getPropertyComplianceData(address);
 setPropertyData(data);
 
 // Determine former council area for Inner West properties
 const councilArea = PropertyDataService.determineFormerCouncilArea(data);
 setFormerCouncilArea(councilArea);
 } catch (err) {
 setError(err instanceof Error ? err.message : 'Failed to load property data');
 } finally {
 setLoading(false);
 }
 };
 
 // Check if all required fields are filled
 const isFormComplete = () => {
 return (
 proposal.height > 0 &&
 proposal.fsr > 0 &&
 proposal.rear_setback > 0 &&
 proposal.side_setback > 0 &&
 proposal.front_setback > 0
 );
 };
 
 // Calculate compliance using deterministic engine
 const checkCompliance = async () => {
 if (!isFormComplete()) {
 setError('Please fill in all required fields');
 return;
 }
 
 if (!propertyData) return;
 
 try {
 // Use deterministic compliance engine
 const complianceResults = await complianceEngine.checkCompliance(
 propertyData,
 proposal,
 formerCouncilArea || undefined
 );
 setResults(complianceResults);
 } catch (error) {
 console.error('Compliance check failed:', error);
 setError('Compliance check failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
 }
 };
 
 if (error) {
 return (
 <div className="compliance-checker error">
 <h2>Development Compliance Checker</h2>
 <div className="error-message">{error}</div>
 <button onClick={() => setError(null)}>Try Again</button>
 </div>
 );
 }

 return (
 <div className="compliance-checker">
 <h2>Development Compliance Checker</h2>
 
 <div className="address-search">
 <label htmlFor="address-autocomplete">Property Address:</label>
 <input
 id="address-autocomplete"
 type="text"
 value={address}
 onChange={(e) => setAddress(e.target.value)}
 placeholder={isMapLoaded ? "Start typing an address..." : "Enter full address (e.g., 14 Hunter Street, Lewisham NSW 2049)"}
 className="address-input"
 title={isMapLoaded ? "Google Autocomplete enabled" : "Manual address entry"}
 />
 <button 
 onClick={fetchPropertyData}
 disabled={loading || !address.trim()}
 style={{ marginLeft: '10px', padding: '8px 15px' }}
 >
 {loading ? 'Searching...' : 'Search Property'}
 </button>
 {loading && <div className="loading">Loading property data...</div>}
 </div>
 
 {propertyData && (
 <div className="main-content">
 <div className="property-summary">
 <h3>{propertyData.address}</h3>
 <div className="property-details">
 <p><strong>Zone:</strong> {propertyData.zoneDescription}</p>
 <p><strong>Property Area:</strong> {propertyData.propertyArea}</p>
 <p><strong>Land Value:</strong> {propertyData.landValue} ({propertyData.valuationDate})</p>
 <p><strong>LGA:</strong> {propertyData.constraints.lga}</p>
 {formerCouncilArea && (
 <p><strong>Former Council Area:</strong> {formerCouncilArea}</p>
 )}
 
 {/* Heritage Information */}
 {propertyData.heritage?.isHeritage && (
 <div className="heritage-info">
 <p><strong>Heritage:</strong> {propertyData.heritage.heritageType}</p>
 {propertyData.heritage.heritageClause && (
 <p><strong>Heritage Clause:</strong> {propertyData.heritage.heritageClause}</p>
 )}
 </div>
 )}
 
 {/* Environmental Constraints */}
 {(propertyData.environmental?.floodProne || propertyData.environmental?.bushfireProne || propertyData.environmental?.acidSulfateSoils) && (
 <div className="environmental-info">
 <h4>Environmental Constraints:</h4>
 {propertyData.environmental.floodProne && (
 <p><strong>Flood Prone Area</strong></p>
 )}
 {propertyData.environmental.bushfireProne && (
 <p><strong>Bushfire Prone Area</strong></p>
 )}
 {propertyData.environmental.acidSulfateSoils && (
 <p><strong>Acid Sulfate Soils:</strong> {propertyData.environmental.acidSulfateSoils}</p>
 )}
 {propertyData.environmental.basixClimate && (
 <p><strong>BASIX Climate Zone:</strong> {propertyData.environmental.basixClimate}</p>
 )}
 {propertyData.environmental.basixWater && (
 <p><strong>BASIX Water Target:</strong> {propertyData.environmental.basixWater}</p>
 )}
 </div>
 )}
 </div>
 </div>
 
 <div className="compliance-form">
 <h4>Enter Your Development Proposal</h4>
 
 <div className="input-group">
 <div className="form-field">
 <label>
 Proposed Height (m):
 <input 
 type="number" 
 value={proposal.height || ''} 
 onChange={e => setProposal({...proposal, height: parseFloat(e.target.value)})} 
 step="0.1"
 min="0"
 placeholder={propertyData.constraints.maxHeight ? `Max: ${propertyData.constraints.maxHeight}m` : "Enter height"}
 />
 </label>
 </div>
 
 <div className="form-field">
 <label>
 Proposed FSR:
 <input 
 type="number" 
 value={proposal.fsr || ''} 
 onChange={e => setProposal({...proposal, fsr: parseFloat(e.target.value)})} 
 step="0.01"
 min="0"
 placeholder={propertyData.constraints.maxFsr ? `Max: ${propertyData.constraints.maxFsr}` : "Enter FSR"}
 />
 </label>
 </div>
 
 <div className="form-field">
 <label>
 Proposed Rear Setback (m):
 <input 
 type="number" 
 value={proposal.rear_setback || ''} 
 onChange={e => setProposal({...proposal, rear_setback: parseFloat(e.target.value)})} 
 step="0.1"
 min="0"
 placeholder="Min: 6.0m (standard R2)"
 />
 </label>
 </div>
 
 <div className="form-field">
 <label>
 Proposed Side Setback (m):
 <input 
 type="number" 
 value={proposal.side_setback || ''} 
 onChange={e => setProposal({...proposal, side_setback: parseFloat(e.target.value)})} 
 step="0.1"
 min="0"
 placeholder="Min: 0.9m (Ashfield) / 1.0m (others)"
 />
 </label>
 </div>
 
 <div className="form-field">
 <label>
 Proposed Front Setback (m):
 <input 
 type="number" 
 value={proposal.front_setback || ''} 
 onChange={e => setProposal({...proposal, front_setback: parseFloat(e.target.value)})} 
 step="0.1"
 min="0"
 placeholder="Min: varies by streetscape"
 />
 </label>
 </div>
 </div>
 
 <button 
 className="check-button" 
 disabled={!isFormComplete()}
 onClick={checkCompliance}
 >
 {isFormComplete() ? 'Check Compliance' : 'Complete all fields to check compliance'}
 </button>
 
 <div className="form-hint">
 {isFormComplete() ? '' : 'All height, FSR, and setback fields must be completed'}
 </div>
 </div>
 </div>
 )}
 
 {results.length > 0 && (
 <div className="compliance-results">
 <h4>Compliance Assessment</h4>
 {results.map((result, index) => (
 <div key={index} className={`result-item ${result.compliant ? 'compliant' : 'non-compliant'}`}>
 <div className="result-header">
 {result.compliant ? 'PASS' : 'FAIL'} <strong>{result.type.toUpperCase()}</strong>
 <span className={`confidence ${result.confidence.toLowerCase()}`}>
 {result.confidence}
 </span>
 </div>
 <div className="result-details">
 <p>
 Your proposal: {result.proposed_value}
 {result.type.includes('fsr') ? '' : 'm'} 
 {result.compliant ? ' ≤ ' : ' > '}
 {Array.isArray(result.required_value) ? 
 `${result.required_value[0]}-${result.required_value[1]}` : 
 result.required_value}
 {result.type.includes('fsr') ? '' : 'm'}
 </p>
 {result.mitigation && (
 <div className="mitigation">Fix: {result.mitigation}</div>
 )}
 <div className="source">
 Source: <a href={result.source.url} target="_blank" rel="noopener noreferrer">
 {result.source.document} {result.source.section}
 </a>
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 
 <div className="disclaimer">
 <strong>Data Sources & Confidence:</strong>
 <ul>
 <li><span className="confidence high">HIGH</span> - NSW Planning Portal official data (Height, FSR)</li>
 <li><span className="confidence verified">VERIFIED</span> - Manually verified DCP setback rules</li>
 <li><span className="confidence standard">STANDARD</span> - Industry standard setback values</li>
 </ul>
 This tool uses official NSW government data and manually verified planning rules.
 Final development assessment requires formal council submission.
 </div>
 </div>
 );
}
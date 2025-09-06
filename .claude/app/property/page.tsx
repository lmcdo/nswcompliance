'use client';

import React, { useState, useEffect } from 'react';

// Google Maps API types are declared in google-maps.ts
import { loadGoogleMapsAPI } from '../../../lib/regulatory-engine/google-maps';
import { PropertyDataService } from '../../../lib/property-data';

interface PropertyData {
  propId: number;
  address: string;
  landValue: string;
  valuationDate: string;
  propertyArea: string;
  zoneDescription: string;
  urbanity: string;
  constraints: {
    maxFsr: number | null;
    maxHeight: number | null;
    minLotSize: number | null;
    zone: string | null;
    lga: string | null;
  };
  fsrSource?: {
    clause: string;
    legislationUrl: string;
    epiName: string;
  };
  heightSource?: {
    clause: string;
    legislationUrl: string;
    epiName: string;
  };
  minLotSizeSource?: {
    clause: string;
    legislationUrl: string;
    epiName: string;
  };
  geometry: {
    x: number;
    y: number;
  };
}

interface SetbackRules {
  rear: {
    distance: number;
    height_limit: number;
    source: string;
    source_link: string;
  } | null;
  side: {
    height_limit: number;
    source: string;
    source_link: string;
  } | null;
  front: {
    min_distance: number;
    source: string;
    source_link: string;
  } | null;
}

interface ComplianceResult {
  rule: string;
  compliant: boolean;
  value: number;
  limit: number;
  gap: number;
  source: string;
  sourceLink: string;
  mitigation?: string;
}

export default function PropertyPage() {
  const [propertyData, setPropertyData] = useState<PropertyData | null>(null);
  const [setbackRules, setSetbackRules] = useState<SetbackRules | null>(null);
  const [formerCouncilArea, setFormerCouncilArea] = useState<string | null>(null);
  const [proposal, setProposal] = useState({
    height: 0,
    fsr: 0,
    rearSetback: 0,
    sideSetback: 0,
    frontSetback: 0
  });
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [results, setResults] = useState<ComplianceResult[]>([]);
  
  // Load Google Maps API
  useEffect(() => {
    const loadMaps = async () => {
      try {
        await loadGoogleMapsAPI();
        setIsMapLoaded(true);
      } catch (err) {
        console.error('Failed to load Google Maps API:', err);
        setError('Failed to load address search. Please try again later.');
      }
    };
    
    loadMaps();
  }, []);
  
  // Initialize Google Autocomplete
  useEffect(() => {
    if (!isMapLoaded || !window.google) return;
    
    const input = document.getElementById('address-autocomplete') as HTMLInputElement;
    if (!input) return;
    
    const autocomplete = new window.google.maps.places.Autocomplete(input, {
      types: ['address'],
      componentRestrictions: { country: 'au' },
      fields: ['address_components', 'formatted_address', 'geometry']
    });
    
    autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace();
      if (place.formatted_address) {
        setAddress(place.formatted_address);
      }
    });
  }, [isMapLoaded]);
  
  // Fetch property data when address is set
  useEffect(() => {
    if (!address) return;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Get property data
        const data = await PropertyDataService.getPropertyComplianceData(address);
        setPropertyData(data);
        
        // Get setback rules
        const setbackResponse = await fetch(
          `/api/compliance/setbacks?address=${encodeURIComponent(address)}`
        );
        const setbackData = await setbackResponse.json();
        setSetbackRules(setbackData.setbacks);
        setFormerCouncilArea(setbackData.formerCouncilArea);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load property data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [address]);
  
  // Check if all required fields are filled
  const isFormComplete = () => {
    return (
      proposal.height > 0 &&
      proposal.fsr > 0 &&
      proposal.rearSetback > 0 &&
      proposal.sideSetback > 0 &&
      proposal.frontSetback > 0
    );
  };
  
  // Calculate compliance when form is submitted
  const checkCompliance = () => {
    if (!isFormComplete()) {
      setError('Please fill in all required fields');
      return;
    }
    
    if (!propertyData) return;
    
    const newResults: ComplianceResult[] = [];
    
    // Height check (basic)
    if (propertyData.constraints.maxHeight !== null && proposal.height > 0) {
      const compliant = proposal.height <= propertyData.constraints.maxHeight;
      const gap = propertyData.constraints.maxHeight - proposal.height;
      
      let source = `Source: ${propertyData.constraints.lga} LEP`;
      let sourceLink = '#';
      
      if (propertyData.heightSource) {
        source = `Source: ${propertyData.constraints.lga} ${propertyData.heightSource.epiName} ${propertyData.heightSource.clause}`;
        sourceLink = propertyData.heightSource.legislationUrl;
      }
      
      if (!compliant) {
        newResults.push({
          rule: "Height",
          compliant: false,
          value: proposal.height,
          limit: propertyData.constraints.maxHeight,
          gap: gap,
          source: source,
          sourceLink: sourceLink,
          mitigation: `Reduce height by ${Math.abs(gap).toFixed(1)}m`
        });
      } else {
        newResults.push({
          rule: "Height",
          compliant: true,
          value: proposal.height,
          limit: propertyData.constraints.maxHeight,
          gap: gap,
          source: source,
          sourceLink: sourceLink
        });
      }
    }
    
    // FSR check
    if (propertyData.constraints.maxFsr !== null && proposal.fsr > 0) {
      // Extract lot size from propertyArea string (e.g., "271.9 square metres")
      const lotSizeMatch = propertyData.propertyArea.match(/([\d.]+)/);
      const lotSize = lotSizeMatch ? parseFloat(lotSizeMatch[0]) : null;
      
      const compliant = proposal.fsr <= propertyData.constraints.maxFsr;
      const gap = propertyData.constraints.maxFsr - proposal.fsr;
      
      let source = `Source: ${propertyData.constraints.lga} LEP`;
      let sourceLink = '#';
      
      if (propertyData.fsrSource) {
        source = `Source: ${propertyData.constraints.lga} ${propertyData.fsrSource.epiName} ${propertyData.fsrSource.clause}`;
        sourceLink = propertyData.fsrSource.legislationUrl;
      }
      
      if (!compliant) {
        const deficit = lotSize ? (proposal.fsr - propertyData.constraints.maxFsr) * lotSize : null;
        newResults.push({
          rule: "FSR",
          compliant: false,
          value: proposal.fsr,
          limit: propertyData.constraints.maxFsr,
          gap: gap,
          source: source,
          sourceLink: sourceLink,
          mitigation: deficit 
            ? `Reduce floor area by ${deficit.toFixed(1)}m²` 
            : 'Reduce FSR to comply with limit'
        });
      } else {
        newResults.push({
          rule: "FSR",
          compliant: true,
          value: proposal.fsr,
          limit: propertyData.constraints.maxFsr,
          gap: gap,
          source: source,
          sourceLink: sourceLink
        });
      }
    }
    
    // Rear setback check (using extracted rules)
    if (setbackRules?.rear && proposal.rearSetback > 0) {
      // Check if within the distance where special height limit applies
      if (proposal.rearSetback <= setbackRules.rear.distance) {
        const compliant = proposal.height <= setbackRules.rear.height_limit;
        const gap = setbackRules.rear.height_limit - proposal.height;
        
        if (!compliant) {
          newResults.push({
            rule: "Rear Height Limit",
            compliant: false,
            value: proposal.height,
            limit: setbackRules.rear.height_limit,
            gap: gap,
            source: setbackRules.rear.source,
            sourceLink: setbackRules.rear.source_link,
            mitigation: `Reduce height to ${setbackRules.rear.height_limit}m within ${setbackRules.rear.distance}m of rear boundary`
          });
        }
      }
      
      // Standard rear setback check
      const compliant = proposal.rearSetback >= setbackRules.rear.distance;
      const gap = proposal.rearSetback - setbackRules.rear.distance;
      
      newResults.push({
        rule: "Rear Setback",
        compliant: compliant,
        value: proposal.rearSetback,
        limit: setbackRules.rear.distance,
        gap: gap,
        source: setbackRules.rear.source,
        sourceLink: setbackRules.rear.source_link,
        mitigation: !compliant ? `Increase rear setback to ${setbackRules.rear.distance}m` : undefined
      });
    }
    
    // Side setback check
    if (setbackRules?.side && proposal.sideSetback > 0) {
      const compliant = proposal.height <= setbackRules.side.height_limit;
      const gap = setbackRules.side.height_limit - proposal.height;
      
      newResults.push({
        rule: "Side Height Limit",
        compliant: compliant,
        value: proposal.height,
        limit: setbackRules.side.height_limit,
        gap: gap,
        source: setbackRules.side.source,
        sourceLink: setbackRules.side.source_link,
        mitigation: !compliant ? `Reduce height to ${setbackRules.side.height_limit}m` : undefined
      });
    }
    
    // Front setback check
    if (setbackRules?.front && proposal.frontSetback > 0) {
      const compliant = proposal.frontSetback >= setbackRules.front.min_distance;
      const gap = proposal.frontSetback - setbackRules.front.min_distance;
      
      newResults.push({
        rule: "Front Setback",
        compliant: compliant,
        value: proposal.frontSetback,
        limit: setbackRules.front.min_distance,
        gap: gap,
        source: setbackRules.front.source,
        sourceLink: setbackRules.front.source_link,
        mitigation: !compliant ? `Increase front setback to ${setbackRules.front.min_distance}m` : undefined
      });
    }
    
    setResults(newResults);
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
    <div className="compliance-checker" style={{ display: 'flex', gap: '40px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Left Column - Input Form */}
      <div className="left-column" style={{ flex: '0 0 400px', paddingRight: '20px' }}>
        <h2>Development Compliance Checker</h2>
        
        <div className="address-search" style={{ marginBottom: '30px' }}>
          <label htmlFor="address-autocomplete" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Property Address:
          </label>
          <input
            id="address-autocomplete"
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Start typing an address..."
            className="address-input"
            style={{ width: '100%', padding: '12px', fontSize: '14px', border: '2px solid #ddd', borderRadius: '6px' }}
          />
          <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>
            ✅ Google Autocomplete enabled - start typing for suggestions
          </div>
          {loading && <div className="loading" style={{ marginTop: '8px', color: '#666' }}>Loading property data...</div>}
        </div>
        
        {propertyData && (
          <>
            <div className="property-summary" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <h3 style={{ margin: '0 0 15px 0', fontSize: '18px', color: '#1e40af' }}>{propertyData.address}</h3>
              <div className="property-details" style={{ fontSize: '14px', lineHeight: '1.6' }}>
                <p style={{ margin: '4px 0' }}><strong>Zone:</strong> {propertyData.zoneDescription}</p>
                {formerCouncilArea && (
                  <p style={{ margin: '4px 0' }}><strong>Former Council:</strong> {formerCouncilArea}</p>
                )}
                <p style={{ margin: '4px 0', fontSize: '12px', color: '#666' }}>
                  H: {propertyData.constraints.maxHeight}m | FSR: {propertyData.constraints.maxFsr}
                </p>
              </div>
            </div>
            
            <div className="compliance-form">
              <h4 style={{ marginBottom: '20px', color: '#374151' }}>Enter Your Proposal</h4>
              
              <div className="input-group" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {propertyData.constraints.maxHeight !== null && (
                  <div className="form-field">
                    <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      Height (m):
                    </label>
                    <input 
                      type="number" 
                      value={proposal.height || ''} 
                      onChange={e => setProposal({...proposal, height: parseFloat(e.target.value)})} 
                      step="0.1"
                      min="0"
                      placeholder={`Max: ${propertyData.constraints.maxHeight}m`}
                      style={{ width: '120px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px' }}
                    />
                  </div>
                )}
                
                {propertyData.constraints.maxFsr !== null && (
                  <div className="form-field">
                    <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      FSR:
                    </label>
                    <input 
                      type="number" 
                      value={proposal.fsr || ''} 
                      onChange={e => setProposal({...proposal, fsr: parseFloat(e.target.value)})} 
                      step="0.01"
                      min="0"
                      placeholder={`Max: ${propertyData.constraints.maxFsr}`}
                      style={{ width: '120px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px' }}
                    />
                  </div>
                )}
                
                {setbackRules?.rear && (
                  <div className="form-field">
                    <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      Rear Setback (m):
                    </label>
                    <input 
                      type="number" 
                      value={proposal.rearSetback || ''} 
                      onChange={e => setProposal({...proposal, rearSetback: parseFloat(e.target.value)})} 
                      step="0.1"
                      min="0"
                      placeholder={`Min: ${setbackRules.rear.distance}m`}
                      style={{ width: '120px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px' }}
                    />
                  </div>
                )}
                
                {setbackRules?.side && (
                  <div className="form-field">
                    <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      Side Setback (m):
                    </label>
                    <input 
                      type="number" 
                      value={proposal.sideSetback || ''} 
                      onChange={e => setProposal({...proposal, sideSetback: parseFloat(e.target.value)})} 
                      step="0.1"
                      min="0"
                      placeholder="Min: 1.0m"
                      style={{ width: '120px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px' }}
                    />
                  </div>
                )}
                
                {setbackRules?.front && (
                  <div className="form-field">
                    <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      Front Setback (m):
                    </label>
                    <input 
                      type="number" 
                      value={proposal.frontSetback || ''} 
                      onChange={e => setProposal({...proposal, frontSetback: parseFloat(e.target.value)})} 
                      step="0.1"
                      min="0"
                      placeholder={`Min: ${setbackRules.front.min_distance}m`}
                      style={{ width: '120px', padding: '8px', fontSize: '16px', border: '1px solid #d1d5db', borderRadius: '4px' }}
                    />
                  </div>
                )}
              </div>
              
              <button 
                className="check-button" 
                disabled={!isFormComplete()}
                onClick={checkCompliance}
                style={{
                  width: '100%',
                  padding: '14px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  backgroundColor: isFormComplete() ? '#10b981' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  marginTop: '24px',
                  cursor: isFormComplete() ? 'pointer' : 'not-allowed'
                }}
              >
                Check Compliance
              </button>
              
              {!isFormComplete() && (
                <div className="form-hint" style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                  All fields must be completed
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Right Column - Results */}
      <div className="right-column" style={{ flex: 1 }}>
        {results.length > 0 && (
          <div className="compliance-results">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
              <h3 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
                {results.some(r => !r.compliant) ? '❌ NON-COMPLIANT' : '✅ COMPLIANT'}
              </h3>
              <div style={{ textAlign: 'right', fontSize: '14px', color: '#6b7280' }}>
                <div>{results.length} rules checked</div>
                <div>{results.filter(r => !r.compliant).length} issues found</div>
                <div>1 semantic rules</div>
              </div>
            </div>

            <div style={{ display: 'grid', gap: '16px' }}>
              {results.map((result, index) => (
                <div key={index} 
                     className={`result-item ${result.compliant ? 'compliant' : 'non-compliant'}`}
                     style={{
                       padding: '20px',
                       border: `2px solid ${result.compliant ? '#10b981' : '#ef4444'}`,
                       borderRadius: '8px',
                       backgroundColor: result.compliant ? '#f0fdf4' : '#fef2f2'
                     }}>
                  <div className="result-header" style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: result.compliant ? '#059669' : '#dc2626' }}>
                      {result.compliant ? '✅' : '❌'} {result.rule} {result.compliant ? 'COMPLIES' : 'VIOLATION'}
                    </div>
                  </div>
                  <div className="result-details">
                    <p style={{ margin: '8px 0', fontSize: '16px' }}>
                      <strong>Your proposal:</strong> {result.value}{result.rule === 'FSR' ? '' : 'm'} 
                      {result.compliant ? ' ≤ ' : ' > '}
                      <strong>{result.limit}{result.rule === 'FSR' ? '' : 'm'}</strong>
                    </p>
                    {result.mitigation && (
                      <div className="mitigation" style={{ 
                        margin: '12px 0', 
                        padding: '12px', 
                        backgroundColor: '#fef3c7', 
                        border: '1px solid #f59e0b',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}>
                        <strong>Fix:</strong> {result.mitigation}
                      </div>
                    )}
                    <div className="source" style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                      Source: <a href={result.sourceLink} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>
                        {result.source}
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Summary Section */}
            <div style={{ marginTop: '32px', padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 16px 0', color: '#374151' }}>Source Authority</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', fontSize: '14px' }}>
                <div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981' }}>1</div>
                  <div style={{ color: '#6b7280' }}>Semantic Rules</div>
                </div>
                <div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6' }}>4</div>
                  <div style={{ color: '#6b7280' }}>Manual Rules</div>
                </div>
                <div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }}>2</div>
                  <div style={{ color: '#6b7280' }}>High Confidence</div>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <h5 style={{ margin: '0 0 8px 0', color: '#374151' }}>Next Steps</h5>
                  <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#6b7280' }}>
                    <li>Address {results.filter(r => !r.compliant).length} high-priority compliance issues</li>
                    <li>Review semantic rule interpretations with planning consultant</li>
                    <li>Reference source documents for regulatory authority citations</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {results.length === 0 && propertyData && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
            <h3>Ready for Compliance Check</h3>
            <p>Complete all fields in the left panel and click "Check Compliance" to see results here.</p>
          </div>
        )}
      </div>
      
      <div className="disclaimer" style={{ 
        position: 'fixed', 
        bottom: '20px', 
        right: '20px', 
        fontSize: '11px', 
        color: '#6b7280',
        backgroundColor: 'white',
        padding: '8px 12px',
        border: '1px solid #e5e7eb',
        borderRadius: '6px',
        maxWidth: '300px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        This tool uses council-published constraints from official planning documents. 
        Final development assessment requires council submission.
      </div>
    </div>
  );
}
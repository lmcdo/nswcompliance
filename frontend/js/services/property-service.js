import { API_CONFIG } from '../config/api-config.js';
import { getConnectionStatus, getPropertyIntelligence, getPropertyCompleteAssessment, getCouncilValidation, calculateCouncilSetbacks } from './api-service.js';
import { storePropertyIntelligenceContent, storeRegulatoryRequirementsContent } from '../components/tab-manager.js';

// Global variables
let selectedCoordinates = null;

// Main property analysis function
export async function analyzeProperty() {
    const address = document.getElementById('address').value.trim();
    const analyzeBtn = document.getElementById('analyze-btn');
    const intelligenceDiv = document.getElementById('property-intelligence');
    
    if (!address) {
        alert('Please enter a property address');
        return;
    }
    
    if (!getConnectionStatus()) {
        alert('API server is offline. Please start the FastAPI server first.');
        return;
    }
    
    // Show loading state
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';
    
    try {
        // Use exact Google Places formatted address
        let finalAddress = address;
        if (window.selectedPlaceInfo && window.selectedPlaceInfo.originalAddress) {
            finalAddress = window.selectedPlaceInfo.originalAddress;
            console.log('Using Google Places formatted address:', finalAddress);
        }
        
        // Use basic property intelligence endpoint with full NSW data
        let basicApiUrl = `${API_CONFIG.baseURL}${API_CONFIG.endpoints.propertyIntelligence}?address=${encodeURIComponent(finalAddress)}&include_raw_nsw_data=true`;
        if (selectedCoordinates) {
            basicApiUrl += `&lat=${selectedCoordinates.lat}&lng=${selectedCoordinates.lng}`;
            console.log('Sending coordinates with request:', selectedCoordinates);
        }
        
        const response = await fetch(basicApiUrl);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Property intelligence basic data:', data);
        
        // The basic endpoint should now include raw NSW data with include_raw_nsw_data=true
        console.log('Checking if basic response includes raw NSW planning data...');
        
        // Store for later use
        window.currentPropertyData = data;
        
        // Display the enhanced property info including planning instruments
        displayBasicPropertyInfo(data);
        intelligenceDiv.style.display = 'block';
        
    } catch (error) {
        alert(`Analysis failed: ${error.message}`);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze Property';
    }
}

// Display basic property information
function displayBasicPropertyInfo(data) {
    console.log('Displaying basic property info with NSW API data:', data);
    
    // Store property data globally for connected requirements
    window.currentPropertyIntelligence = data;
    
    const locationDiv = document.getElementById('location-details');
    const controlsDiv = document.getElementById('planning-controls');
    
    if (!locationDiv || !controlsDiv) {
        console.error('Required divs not found');
        return;
    }
    
    // Location Details (without duplicate header)
    locationDiv.innerHTML = `
        <div class="intel-row">
            <span class="intel-label">Address:</span>
            <span class="intel-value">${data.address}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Property ID:</span>
            <span class="intel-value">${data.prop_id || 'Not found'}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Local Government:</span>
            <span class="intel-value">${data.lga_name || 'Unknown'}</span>
        </div>
    `;
    
    // Planning Controls - Enhanced with NSW API data (without duplicate header)
    let planningControlsHTML = ``;
    
    // Basic controls
    planningControlsHTML += `
        <div class="intel-row">
            <span class="intel-label">Zone:</span>
            <span class="intel-value">${data.zone || 'Unknown'} ${data.zone_description ? `(${data.zone_description})` : ''}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Height Limit:</span>
            <span class="intel-value">${data.height_limit || 'Not specified'} ${data.height_units || ''}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">FSR Limit:</span>
            <span class="intel-value">${data.fsr_limit || 'Not specified'}${data.fsr_limit && data.fsr_limit !== 'Not specified' ? ' sq metres' : ''}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Land Area:</span>
            <span class="intel-value">${data.land_area || 'Not available'}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Land Value:</span>
            <span class="intel-value">${data.land_value ? data.land_value.trim() : 'Not available'}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Heritage Status:</span>
            <span class="intel-value">${data.heritage_status || 'No heritage constraints'}</span>
        </div>
        <div class="intel-row">
            <span class="intel-label">Applicable LEP:</span>
            <span class="intel-value">${data.applicable_lep || 'Unknown'}</span>
        </div>
    `;
    
    // Add NSW API specific data if available
    console.log('Full data object keys:', Object.keys(data));
    console.log('Looking for NSW planning data in response...');
    
    // Display ALL NSW planning data layers
    if (data.planning_controls) {
        console.log('Displaying full NSW Planning Controls:', data.planning_controls);
        
        // Display each planning layer with full details
        data.planning_controls.forEach(layer => {
            if (!layer.results || layer.results.length === 0) return;
            
            const layerName = layer.layerName;
            let displayName = layerName;
            let results = layer.results;
            
            // Special handling for each layer type
            switch (layerName) {
                case 'Land Zoning Map':
                    results.forEach(result => {
                        const instrument = result['EPI Name'] || '';
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Zoning:</span>
                                <span class="intel-value">${result.title || result.Zone} - ${result['Land Use'] || ''}<br>
                                <em style="font-size: 0.9em; color: #666;">${instrument}</em></span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Height of Buildings Map':
                    results.forEach(result => {
                        const instrument = result['EPI Name'] || '';
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Height Limit:</span>
                                <span class="intel-value">${result.title} (${result['Legislative Clause'] || ''})<br>
                                <em style="font-size: 0.9em; color: #666;">${instrument}</em></span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Floor Space Ratio Map':
                    // Combine FSR results into single display
                    const fsrMain = results.find(r => r.title || r['Floor Space Ratio']);
                    const fsrAdditional = results.filter(r => !r.title && !r['Floor Space Ratio'] && r['Legislative Clause']);
                    
                    if (fsrMain) {
                        const fsr = fsrMain.title || (fsrMain['Floor Space Ratio'] ? `${fsrMain['Floor Space Ratio']}:1` : '');
                        const clause = fsrMain['Legislative Clause'] || '';
                        const additionalClauses = fsrAdditional.map(r => r['Legislative Clause']).join(', ');
                        const additional = fsrMain['Additional Controls'] ? ` (${fsrMain['Additional Controls']})` : '';
                        const instrument = fsrMain['EPI Name'] || '';
                        
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">FSR:</span>
                                <span class="intel-value">${fsr} ${clause}${additionalClauses ? '; ' + additionalClauses : ''}${additional}<br>
                                <em style="font-size: 0.9em; color: #666;">${instrument}</em></span>
                            </div>
                        `;
                    } else {
                        // Fallback for cases where we only have additional clauses
                        results.forEach(result => {
                            const clause = result['Legislative Clause'] || '';
                            const instrument = result['EPI Name'] || '';
                            if (clause) {
                                planningControlsHTML += `
                                    <div class="intel-row">
                                        <span class="intel-label">FSR:</span>
                                        <span class="intel-value">${clause}<br>
                                        <em style="font-size: 0.9em; color: #666;">${instrument}</em></span>
                                    </div>
                                `;
                            }
                        });
                    }
                    break;
                    
                case 'Lot Size Map':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Min Lot Size:</span>
                                <span class="intel-value">${result.title || result['Lot Size'] + ' ' + (result.Units || 'm²')}</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Key Sites Map':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Key Sites:</span>
                                <span class="intel-value">${result.title} (${result['Legislative Clause'] || ''})</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Acid Sulfate Soils Map':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Acid Sulfate Soils:</span>
                                <span class="intel-value">${result.title}</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Special Provisions':
                    const sepps = results.filter(item => item['EPI Type'] === 'SEPP');
                    if (sepps.length > 0) {
                        planningControlsHTML += `
                            <div class="intel-row" style="align-items: flex-start;">
                                <span class="intel-label">State Policies (SEPPs):</span>
                                <span class="intel-value" style="line-height: 1.4;">
                                    <strong>${sepps.length} applicable:</strong><br>
                                    ${sepps.map(sepp => {
                                        let name = sepp['EPI Name'] || sepp.title;
                                        // Add specific values for water use and climate zones
                                        if (sepp['Map Type'] === 'WAT' && sepp['Class']) {
                                            name += ` (${sepp['Class']})`;
                                        }
                                        if (sepp['Map Type'] === 'CLM' && sepp['Class']) {
                                            name += ` (Zone ${sepp['Class']})`;
                                        }
                                        if (sepp['Map Type'] === 'BAL' && sepp['Class']) {
                                            name += ` (Zone ${sepp['Class']})`;
                                        }
                                        return `• ${name}`;
                                    }).join('<br>')}
                                </span>
                            </div>
                        `;
                    }
                    break;
                    
                case 'Local Aboriginal Land Council':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Aboriginal Land Council:</span>
                                <span class="intel-value">${result.title}</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Greater Sydney Tree Canopy Cover 2022':
                case 'Greater Sydney Tree Canopy Cover 2019':
                    results.forEach(result => {
                        const year = layerName.includes('2022') ? '2022' : '2019';
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Tree Canopy (${year}):</span>
                                <span class="intel-value">${result['Canopy %']}%</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Regional Plan Boundary':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">Regional Plan:</span>
                                <span class="intel-value">${result.title}</span>
                            </div>
                        `;
                    });
                    break;
                    
                case 'Land Application Map':
                    results.forEach(result => {
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">LEP Coverage:</span>
                                <span class="intel-value">${result.title} (${result.Type})</span>
                            </div>
                        `;
                    });
                    break;
                    
                default:
                    // Generic display for any other layers
                    results.forEach(result => {
                        const title = result.title || result['EPI Name'] || layerName;
                        planningControlsHTML += `
                            <div class="intel-row">
                                <span class="intel-label">${layerName}:</span>
                                <span class="intel-value">${title}</span>
                            </div>
                        `;
                    });
            }
        });
    }
    
    controlsDiv.innerHTML = planningControlsHTML;
}

// Enhanced complete assessment
export async function getEnhancedCompleteAssessment() {
    const address = document.getElementById('address').value.trim();
    
    if (!address) {
        alert('Please enter a property address first');
        return;
    }
    
    if (!getConnectionStatus()) {
        alert('API server is offline. Please start the FastAPI server first.');
        return;
    }
    
    try {
        console.log('Getting enhanced complete assessment for:', address);
        
        // Use the complete assessment endpoint
        const response = await getPropertyCompleteAssessment(address);
        
        if (!response.success) {
            throw new Error(response.error || 'Assessment failed');
        }
        
        const data = response.data;
        console.log('Complete assessment data:', data);
        
        // Display in property intelligence tab
        displayEnhancedPropertyIntelligence(data);
        
        // Get connected requirements
        await getConnectedRequirements();
        
    } catch (error) {
        console.error('Enhanced assessment error:', error);
        alert(`Enhanced assessment failed: ${error.message}`);
    }
}

// Display enhanced property intelligence
function displayEnhancedPropertyIntelligence(data) {
    const contentDiv = document.querySelector('#property-intelligence-content');
    if (!contentDiv) {
        console.error('Property intelligence content div not found');
        return;
    }
    
    let html = `
        <div class="property-context-header">
            <h3>🏠 Property Intelligence Report</h3>
            <p><strong>Address:</strong> ${data.address}</p>
            
            <div class="context-tags">
                ${data.zone ? `<span class="zone-tag">${data.zone}</span>` : ''}
                ${data.lga_name ? `<span class="lga-tag">${data.lga_name}</span>` : ''}
                ${data.heritage_status && data.heritage_status !== 'No heritage constraints' ? `<span class="heritage-tag">Heritage</span>` : ''}
            </div>
            
            <div class="applicable-documents">
                📋 Applicable Documents: ${data.applicable_lep || 'LEP'}, DCPs, SEPPs
            </div>
        </div>
    `;
    
    // Critical controls if available
    if (data.height_limit || data.fsr_limit) {
        html += `<div class="critical-controls-section">`;
        
        if (data.height_limit) {
            html += `
                <div class="critical-alert">
                    <div class="alert-header">
                        <div>
                            <span class="alert-icon">📏</span>
                            <strong>Maximum Building Height</strong>
                        </div>
                        <span class="status-badge">Critical Control</span>
                    </div>
                    <div class="main-value">${data.height_limit} ${data.height_units || ''}</div>
                    <div class="source">Source: ${data.applicable_lep || 'Local Environmental Plan'}</div>
                    ${data.height_clause ? `<div class="measurement">Clause: ${data.height_clause}</div>` : ''}
                </div>
            `;
        }
        
        html += `</div>`;
    }
    
    // Important controls grid
    html += `
        <div class="important-controls-grid">
            <div class="control-card">
                <div class="card-header">
                    <h4>🏛️ Zoning</h4>
                    <span class="priority-badge important">Important</span>
                </div>
                <div class="control-value">${data.zone || 'Unknown'}</div>
                <div class="measurement-note">${data.zone_description || 'Zone description not available'}</div>
                <div class="card-footer">
                    Source: ${data.applicable_lep || 'Local Environmental Plan'}
                </div>
            </div>
            
            <div class="control-card">
                <div class="card-header">
                    <h4>📐 Floor Space Ratio</h4>
                    <span class="priority important">High</span>
                </div>
                <div class="control-value">${data.fsr_limit || 'Not specified'}</div>
                <div class="measurement-note">Maximum floor space ratio for the site</div>
                <div class="card-footer">
                    Source: ${data.applicable_lep || 'Local Environmental Plan'}
                </div>
            </div>
            
            <div class="control-card">
                <div class="card-header">
                    <h4>🏛️ Heritage</h4>
                    <span class="priority important">Check</span>
                </div>
                <div class="control-value">${data.heritage_status || 'No constraints'}</div>
                <div class="measurement-note">Heritage conservation requirements</div>
                <div class="card-footer">
                    Source: Heritage databases and LEP
                </div>
            </div>
        </div>
    `;
    
    // NSW Planning Data section
    if (data.nsw_planning_data) {
        html += displayNSWPlanningData(data.nsw_planning_data);
    }
    
    contentDiv.innerHTML = html;
    
    // Store content for tab switching
    storePropertyIntelligenceContent(html);
}

// Display NSW Planning Data (SEPPs, Special Conditions, etc.)
function displayNSWPlanningData(planningData) {
    let html = `<div class="nsw-planning-section">
        <h3>🏛️ NSW Planning Controls</h3>
        <div class="planning-data-summary">
            <p>Comprehensive NSW Government planning data retrieved from official APIs</p>
        </div>
    `;
    
    // State Environmental Planning Policies (SEPPs)
    if (planningData.sepps && planningData.sepps.length > 0) {
        html += `
            <div class="document-group">
                <h5>📜 State Environmental Planning Policies (${planningData.sepps.length} SEPPs)</h5>
                <div class="sepp-list">
        `;
        
        planningData.sepps.forEach((sepp, index) => {
            // Handle different SEPP data structures from NSW API
            const seppName = sepp.name || sepp.title || sepp.instrument_name || sepp.planningInstrumentName || `SEPP ${index + 1}`;
            const seppDescription = sepp.description || sepp.purpose || sepp.summary || 'State environmental planning policy';
            const seppStatus = sepp.status || sepp.gazetted || sepp.current_status || 'Active';
            const seppDate = sepp.gazetted_date || sepp.commencement_date || sepp.date_made || '';
            
            html += `
                <div class="sepp-item">
                    <div class="sepp-header">
                        <strong>${seppName}</strong>
                        <span class="status-badge sepp-active">${seppStatus}</span>
                    </div>
                    <div class="sepp-description">${seppDescription}</div>
                    ${seppDate ? `<div class="sepp-date">📅 ${seppDate}</div>` : ''}
                    ${sepp.applicability || sepp.applies_to ? `<div class="sepp-applicability"><strong>Applies to:</strong> ${sepp.applicability || sepp.applies_to}</div>` : ''}
                    ${sepp.key_provisions ? `<div class="sepp-provisions"><strong>Key provisions:</strong> ${sepp.key_provisions}</div>` : ''}
                </div>
            `;
        });
        
        html += `</div></div>`;
    } else {
        html += `
            <div class="document-group">
                <h5>📜 State Environmental Planning Policies (SEPPs)</h5>
                <div class="no-data">No specific SEPPs identified for this property. General state policies may still apply.</div>
            </div>
        `;
    }
    
    // Special Conditions
    if (planningData.special_conditions && planningData.special_conditions.length > 0) {
        html += `
            <div class="document-group">
                <h5>⚠️ Special Planning Conditions (${planningData.special_conditions.length} conditions)</h5>
                <div class="conditions-list">
        `;
        
        planningData.special_conditions.forEach((condition, index) => {
            const conditionName = condition.name || condition.title || condition.condition_type || `Special Condition ${index + 1}`;
            const conditionDesc = condition.description || condition.details || condition.requirements || 'Special planning condition applies';
            const conditionImpact = condition.impact || condition.implications || '';
            const conditionAuth = condition.authority || condition.imposed_by || 'Planning Authority';
            
            html += `
                <div class="condition-item">
                    <div class="condition-header">
                        <strong>${conditionName}</strong>
                        <span class="status-badge condition-active">Active</span>
                    </div>
                    <div class="condition-description">${conditionDesc}</div>
                    ${conditionImpact ? `<div class="condition-impact"><strong>Impact:</strong> ${conditionImpact}</div>` : ''}
                    <div class="condition-authority"><strong>Authority:</strong> ${conditionAuth}</div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    } else {
        html += `
            <div class="document-group">
                <h5>⚠️ Special Planning Conditions</h5>
                <div class="no-data">No special conditions identified for this property.</div>
            </div>
        `;
    }
    
    // Other Planning Instruments
    if (planningData.other_instruments && planningData.other_instruments.length > 0) {
        html += `
            <div class="document-group">
                <h5>📋 Other Planning Instruments (${planningData.other_instruments.length} instruments)</h5>
                <div class="instruments-list">
        `;
        
        planningData.other_instruments.forEach((instrument, index) => {
            const instrName = instrument.name || instrument.title || instrument.instrument_name || `Planning Instrument ${index + 1}`;
            const instrType = instrument.type || instrument.instrument_type || 'Planning Instrument';
            const instrDesc = instrument.description || instrument.purpose || 'Planning instrument applies to this property';
            const instrAuth = instrument.authority || instrument.responsible_authority || 'Planning Authority';
            
            html += `
                <div class="instrument-item">
                    <div class="instrument-header">
                        <strong>${instrName}</strong>
                        <span class="instrument-type">${instrType}</span>
                    </div>
                    <div class="instrument-description">${instrDesc}</div>
                    <div class="instrument-authority"><strong>Authority:</strong> ${instrAuth}</div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    } else {
        html += `
            <div class="document-group">
                <h5>📋 Other Planning Instruments</h5>
                <div class="no-data">No additional planning instruments identified.</div>
            </div>
        `;
    }
    
    // Add a note about data source
    html += `
        <div class="data-source-note">
            <p><small>📊 <strong>Data Source:</strong> NSW Planning Portal API - Real-time government planning data</small></p>
        </div>
    `;
    
    html += `</div>`;
    
    return html;
}

// Get connected requirements
export async function getConnectedRequirements() {
    if (!window.currentPropertyIntelligence) {
        console.warn('No property intelligence data available for connected requirements');
        return;
    }
    
    console.log('Getting connected requirements for current property');
    
    const contentDiv = document.querySelector('#regulatory-requirements-content');
    if (!contentDiv) {
        console.error('Regulatory requirements content div not found');
        return;
    }
    
    contentDiv.innerHTML = '<div class="loading">Loading connected regulatory requirements...</div>';
    
    try {
        const response = await getCouncilValidation(window.currentPropertyIntelligence.address);
        
        if (!response.success) {
            throw new Error(response.error || 'Failed to get connected requirements');
        }
        
        const data = response.data;
        console.log('Connected requirements data:', data);
        
        displayConnectedRequirements(data);
        
    } catch (error) {
        console.error('Connected requirements error:', error);
        contentDiv.innerHTML = `<div class="error">Failed to load connected requirements: ${error.message}</div>`;
    }
}

// Display connected requirements
function displayConnectedRequirements(data) {
    const contentDiv = document.querySelector('#regulatory-requirements-content');
    if (!contentDiv) return;
    
    let html = `
        <div class="connected-requirements-panel">
            <h3>🔗 Connected Regulatory Requirements</h3>
            <p>Database-driven compliance requirements for this property</p>
        </div>
    `;
    
    if (data.council_citations && data.council_citations.length > 0) {
        html += `<div class="council-validation-panel">
            <div class="validation-summary">
                Found ${data.council_citations.length} relevant regulatory provisions from Inner West Council documents.
            </div>
        `;
        
        // Group by document
        const groupedCitations = {};
        data.council_citations.forEach(citation => {
            const doc = citation.document || 'Unknown Document';
            if (!groupedCitations[doc]) {
                groupedCitations[doc] = [];
            }
            groupedCitations[doc].push(citation);
        });
        
        Object.entries(groupedCitations).forEach(([document, citations]) => {
            html += `
                <div class="document-group">
                    <h5>${document}</h5>
            `;
            
            citations.forEach(citation => {
                html += `
                    <div class="council-citation">
                        <button class="clause-citation" onclick="toggleClause('${citation.clause_id}')">
                            <div class="clause-header">
                                <div>
                                    <span class="clause-ref">${citation.clause_ref}</span>
                                    <span class="section-title">${citation.section_title || 'Regulatory Requirement'}</span>
                                    <span class="confidence-badge">High</span>
                                </div>
                                <span class="clause-arrow" id="arrow-${citation.clause_id}">▼</span>
                            </div>
                        </button>
                        <div class="clause-content" id="content-${citation.clause_id}">
                            <div class="authority">Authority: ${citation.document}</div>
                            ${citation.text_before ? `<div class="context-before">Context: "${citation.text_before.substring(0, 100)}..."</div>` : ''}
                            <div class="full-text">${citation.full_text}</div>
                            ${citation.text_after ? `<div class="context-after">Continues: "${citation.text_after.substring(0, 100)}..."</div>` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += `</div>`;
        });
        
        html += `</div>`;
    } else {
        html += `<div class="error">No connected regulatory requirements found in the database.</div>`;
    }
    
    contentDiv.innerHTML = html;
    
    // Store content for tab switching
    storeRegulatoryRequirementsContent(html);
}

// Toggle clause content
export async function toggleClause(clauseId) {
    const content = document.getElementById(`content-${clauseId}`);
    const arrow = document.getElementById(`arrow-${clauseId}`);
    
    if (content && arrow) {
        if (content.classList.contains('open')) {
            content.classList.remove('open');
            arrow.classList.remove('expanded');
        } else {
            content.classList.add('open');
            arrow.classList.add('expanded');
        }
    }
}

// Set selected coordinates (for Google Places integration)
export function setSelectedCoordinates(coords) {
    selectedCoordinates = coords;
}

// Make functions globally available
window.analyzeProperty = analyzeProperty;
window.getEnhancedCompleteAssessment = getEnhancedCompleteAssessment;
window.getConnectedRequirements = getConnectedRequirements;
window.toggleClause = toggleClause;
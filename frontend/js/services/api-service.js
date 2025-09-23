import { API_CONFIG } from '../config/api-config.js';

// Connection status tracking
let isConnected = false;

// Check API connection
export async function checkConnection() {
 try {
 console.log('Checking connection to:', API_CONFIG.baseURL + API_CONFIG.endpoints.health);
 
 const response = await fetch(API_CONFIG.baseURL + API_CONFIG.endpoints.health);
 console.log('Connection response status:', response.status);
 
 if (response.ok) {
 const data = await response.json();
 console.log('Connection successful, data:', data);
 isConnected = true;
 updateConnectionStatus(true, `Connected to Ultimate Processor (${data.total_citations} citations)`);
 } else {
 console.error('Connection failed with status:', response.status);
 isConnected = false;
 updateConnectionStatus(false, 'Failed to connect to Ultimate Processor');
 }
 } catch (error) {
 console.error('Connection error:', error);
 isConnected = false;
 updateConnectionStatus(false, 'Ultimate Processor unavailable');
 }
}

// Update connection status UI
function updateConnectionStatus(connected, message) {
 const indicator = document.getElementById('status-indicator');
 const statusText = document.getElementById('status-text');
 
 if (indicator && statusText) {
 if (connected) {
 indicator.className = 'status-indicator status-connected';
 } else {
 indicator.className = 'status-indicator status-disconnected';
 }
 statusText.textContent = message;
 }
}

// Generic API request helper
export async function makeApiRequest(endpoint, options = {}) {
 const url = `${API_CONFIG.baseURL}${endpoint}`;
 
 const defaultOptions = {
 method: 'GET',
 headers: {
 'Content-Type': 'application/json',
 },
 ...options
 };
 
 try {
 const response = await fetch(url, defaultOptions);
 
 if (!response.ok) {
 throw new Error(`HTTP error! status: ${response.status}`);
 }
 
 const data = await response.json();
 return { success: true, data };
 
 } catch (error) {
 console.error(`API request failed for ${endpoint}:`, error);
 return { success: false, error: error.message };
 }
}

// Property intelligence API call
export async function getPropertyIntelligence(address) {
 console.log('Getting property intelligence for:', address);
 
 const response = await makeApiRequest(API_CONFIG.endpoints.propertyIntelligence, {
 method: 'POST',
 body: JSON.stringify({ address })
 });
 
 return response;
}

// Property complete assessment API call
export async function getPropertyCompleteAssessment(address) {
 console.log('Getting complete property assessment for:', address);
 
 const response = await makeApiRequest(API_CONFIG.endpoints.propertyComplete, {
 method: 'POST',
 body: JSON.stringify({ address })
 });
 
 return response;
}

// Council validation API call
export async function getCouncilValidation(address) {
 console.log('Getting council validation for:', address);
 
 const response = await makeApiRequest(API_CONFIG.endpoints.councilValidation, {
 method: 'POST',
 body: JSON.stringify({ address })
 });
 
 return response;
}

// Clause citation API call
export async function getClauseCitation(clauseRef) {
 console.log('Getting clause citation for:', clauseRef);
 
 const response = await makeApiRequest(API_CONFIG.endpoints.clauseCitation, {
 method: 'POST',
 body: JSON.stringify({ clause_ref: clauseRef })
 });
 
 return response;
}

// Council setbacks calculation
export async function calculateCouncilSetbacks(address, lotData) {
 console.log('Calculating council setbacks for:', address);
 
 const response = await makeApiRequest(API_CONFIG.endpoints.setbackCalculation, {
 method: 'POST',
 body: JSON.stringify({ 
 address,
 lot_data: lotData 
 })
 });
 
 return response;
}

// Export connection status
export function getConnectionStatus() {
 return isConnected;
}
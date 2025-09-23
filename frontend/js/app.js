// Main application initialization
import { checkConnection } from './services/api-service.js';
import { loadGoogleMapsAPI } from './services/maps-service.js';
import { setupModalEventHandlers } from './components/modal-manager.js';
import { loadVisualGuides } from './components/tab-manager.js';

// Initialize the application
document.addEventListener('DOMContentLoaded', async function() {
 console.log('NSW Planning Compliance Engine - Initializing...');
 
 try {
 // Initialize modal event handlers
 setupModalEventHandlers();
 
 // Check API connection
 await checkConnection();
 
 // Load Google Maps API for address autocomplete
 loadGoogleMapsAPI();
 
 // Load default visual guides
 loadVisualGuides();
 
 // Set default tab to property intelligence
 const defaultTab = document.getElementById('property-intelligence');
 if (defaultTab) {
 defaultTab.classList.add('active');
 }
 
 const defaultButton = document.querySelector('.tab-button');
 if (defaultButton) {
 defaultButton.classList.add('active');
 }
 
 console.log('Application initialized successfully');
 
 } catch (error) {
 console.error('Application initialization error:', error);
 }
 
 // Periodic connection check (every 30 seconds)
 setInterval(checkConnection, 30000);
});

// Global error handler
window.addEventListener('error', function(event) {
 console.error('Global error:', event.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
 console.error('Unhandled promise rejection:', event.reason);
});
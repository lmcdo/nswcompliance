// API Configuration - centralized endpoint management
export const API_CONFIG = {
    // Auto-detect API server or use environment-specific defaults
    baseURL: (() => {
        // Try to use same protocol and host as frontend, different port
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return `http://${window.location.hostname}:8006`;
        }
        // Production fallback - could be configured via environment variables
        return 'http://127.0.0.1:8006';
    })(),
    endpoints: {
        health: '/citations/stats',
        propertyIntelligence: '/property-intelligence',
        propertyComplete: '/property-intelligence-complete',
        councilValidation: '/council-validation',
        clauseCitation: '/clause-citation',
        setbackCalculation: '/calculate-setbacks-council'
    }
};

console.log('API Configuration:', API_CONFIG);
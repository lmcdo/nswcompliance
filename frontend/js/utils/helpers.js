// Utility helper functions

// Format currency values
export function formatCurrency(value) {
    if (!value) return 'Not available';
    return new Intl.NumberFormat('en-AU', {
        style: 'currency',
        currency: 'AUD'
    }).format(value);
}

// Format area values
export function formatArea(area) {
    if (!area) return 'Not available';
    return area.includes('m²') ? area : `${area} m²`;
}

// Sanitize HTML content
export function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Debounce function for search inputs
export function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Generate unique IDs
export function generateId(prefix = 'id') {
    return `${prefix}_${Math.random().toString(36).substr(2, 9)}`;
}

// Show loading state for an element
export function showLoading(element, message = 'Loading...') {
    if (element) {
        element.innerHTML = `<div class="loading">${message}</div>`;
        element.classList.add('loading-state');
    }
}

// Hide loading state for an element
export function hideLoading(element) {
    if (element) {
        element.classList.remove('loading-state');
    }
}

// Show error message
export function showError(element, message) {
    if (element) {
        element.innerHTML = `<div class="error">${sanitizeHTML(message)}</div>`;
    }
}

// Validate Australian address format
export function validateAustralianAddress(address) {
    if (!address || address.trim().length < 5) {
        return false;
    }
    
    // Basic validation - should contain numbers and letters
    const hasNumbers = /\d/.test(address);
    const hasLetters = /[a-zA-Z]/.test(address);
    
    return hasNumbers && hasLetters;
}

// Format document names for display
export function formatDocumentName(docName) {
    if (!docName) return 'Unknown Document';
    
    // Handle common abbreviations
    const abbreviations = {
        'LEP': 'Local Environmental Plan',
        'DCP': 'Development Control Plan',
        'SEPP': 'State Environmental Planning Policy',
        'EP&A': 'Environmental Planning & Assessment'
    };
    
    let formatted = docName;
    Object.entries(abbreviations).forEach(([abbr, full]) => {
        const regex = new RegExp(`\\b${abbr}\\b`, 'gi');
        formatted = formatted.replace(regex, full);
    });
    
    return formatted;
}

// Extract numbers from strings (for heights, FSR, etc.)
export function extractNumber(str) {
    if (!str) return null;
    const match = str.match(/[\d.]+/);
    return match ? parseFloat(match[0]) : null;
}

// Format clause references
export function formatClauseRef(ref) {
    if (!ref) return '';
    
    // Ensure proper formatting for clause references
    // e.g., "4.3(1)(a)" or "Schedule 1, Part 2"
    return ref.replace(/\s+/g, ' ').trim();
}

// Group array items by a property
export function groupBy(array, property) {
    return array.reduce((groups, item) => {
        const key = item[property];
        if (!groups[key]) {
            groups[key] = [];
        }
        groups[key].push(item);
        return groups;
    }, {});
}

// Sort clauses by reference (numerical sorting)
export function sortClausesByRef(clauses) {
    return clauses.sort((a, b) => {
        const refA = a.clause_ref || '';
        const refB = b.clause_ref || '';
        
        // Extract numbers for proper numerical sorting
        const numA = extractNumber(refA) || 0;
        const numB = extractNumber(refB) || 0;
        
        return numA - numB;
    });
}

// Truncate text with ellipsis
export function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

// Check if value is empty or undefined
export function isEmpty(value) {
    return value === null || value === undefined || value === '' || value === 'Not specified' || value === 'Unknown';
}
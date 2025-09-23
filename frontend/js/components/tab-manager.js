// Global variables for tab content storage
let currentPropertyIntelligenceContent = '';
let currentRegulatoryRequirementsContent = '';

// Tab switching functionality
export function switchTab(tabName) {
 try {
 console.log('Starting switchTab for:', tabName);
 
 // Hide all tab contents
 document.querySelectorAll('.tab-content').forEach(tab => {
 tab.classList.remove('active');
 });
 
 // Deactivate all tab buttons
 document.querySelectorAll('.tab-button').forEach(btn => {
 btn.classList.remove('active');
 });
 
 // Show selected tab content
 const targetTab = document.getElementById(tabName);
 if (!targetTab) {
 console.error('Tab not found:', tabName);
 return;
 }
 targetTab.classList.add('active');
 
 // Activate selected tab button - find the button that called this function
 const activeButton = document.querySelector(`button[onclick="switchTab('${tabName}')"]`);
 if (activeButton) {
 activeButton.classList.add('active');
 } else {
 console.warn('Active button not found for tab:', tabName);
 }
 
 console.log('Tab switching completed for:', tabName);
 
 // Restore content when switching tabs
 console.log('Property Intelligence Content Length:', currentPropertyIntelligenceContent.length);
 console.log('Regulatory Requirements Content Length:', currentRegulatoryRequirementsContent.length);
 
 if (tabName === 'property-intelligence' && currentPropertyIntelligenceContent) {
 console.log('Restoring property intelligence content');
 const tabContainer = document.querySelector('.tab-container #property-intelligence');
 const contentDiv = document.querySelector('.tab-container #property-intelligence-content');
 
 console.log('Tab container found:', tabContainer);
 console.log('Content div found:', contentDiv);
 
 contentDiv.innerHTML = currentPropertyIntelligenceContent;
 
 // Fix the content div styles - remove loading class and ensure proper height
 contentDiv.classList.remove('loading');
 contentDiv.style.cssText = 'height: auto !important; min-height: 200px !important; overflow: visible !important; display: block !important;';
 
 // Ensure tab is visible and fix overflow issues
 tabContainer.style.display = 'block';
 tabContainer.style.overflowX = 'visible';
 tabContainer.style.overflowY = 'auto';
 
 console.log('Content div element:', contentDiv);
 console.log('Tab container element:', tabContainer);
 console.log('All elements with property-intelligence-content ID:', document.querySelectorAll('#property-intelligence-content'));
 console.log('All elements with property-intelligence ID:', document.querySelectorAll('#property-intelligence'));
 }
 
 if (tabName === 'regulatory-requirements' && currentRegulatoryRequirementsContent) {
 console.log('Restoring regulatory requirements content');
 const regContentDiv = document.querySelector('.tab-container #regulatory-requirements-content');
 if (regContentDiv) {
 regContentDiv.innerHTML = currentRegulatoryRequirementsContent;
 regContentDiv.classList.remove('loading');
 }
 }
 
 if (tabName === 'visual-guides') {
 loadVisualGuides();
 }
 
 console.log('Tab switch fully completed for:', tabName);
 
 } catch (error) {
 console.error('Error during tab switch:', error);
 console.error('Tab name:', tabName);
 console.error('Error stack:', error.stack);
 }
}

// Store content for later restoration
export function storePropertyIntelligenceContent(content) {
 currentPropertyIntelligenceContent = content;
}

export function storeRegulatoryRequirementsContent(content) {
 currentRegulatoryRequirementsContent = content;
}

// Visual guides loader
export function loadVisualGuides() {
 const visualContent = document.getElementById('visual-guides-content');
 if (!visualContent) return;

 // Placeholder for visual guides - images will be configured to load from database later
 visualContent.innerHTML = `
 <div class="info" style="text-align: center; padding: 40px; background: #f8fafc; border-radius: 8px; color: #64748b;">
 <h3> Visual Guides</h3>
 <p>Visual planning guides will be loaded from the database</p>
 <p><em>Image serving configuration pending</em></p>
 </div>
 `;
}

// Make functions globally available
window.switchTab = switchTab;
// Modal management for image viewing
export function openModal(imageUrl) {
 const modal = document.getElementById('imageModal');
 const modalImg = document.getElementById('modalImage');
 
 if (modal && modalImg) {
 modal.style.display = 'block';
 modalImg.src = imageUrl;
 }
}

export function closeModal() {
 const modal = document.getElementById('imageModal');
 if (modal) {
 modal.style.display = 'none';
 }
}

// Close modal when clicking outside the image
export function setupModalEventHandlers() {
 const modal = document.getElementById('imageModal');
 if (modal) {
 modal.addEventListener('click', (event) => {
 if (event.target === modal) {
 closeModal();
 }
 });
 }

 // Close modal with Escape key
 document.addEventListener('keydown', (event) => {
 if (event.key === 'Escape') {
 closeModal();
 }
 });
}

// Make functions globally available
window.openModal = openModal;
window.closeModal = closeModal;
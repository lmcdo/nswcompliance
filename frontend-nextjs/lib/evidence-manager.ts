export interface Evidence {
 id: string;
 itemId: string;
 filename: string;
 originalName: string;
 fileType: string;
 fileSize: number;
 uploadDate: string;
 uploadedBy: string;
 description?: string;
 tags?: string[];
 status: 'pending' | 'verified' | 'rejected';
 verificationNotes?: string;
}

export interface EvidenceUploadResult {
 success: boolean;
 evidence?: Evidence;
 error?: string;
}

export interface EvidenceManagerConfig {
 maxFileSize: number;
 allowedTypes: string[];
 apiEndpoint: string;
}

export class EvidenceManager {
 private config: EvidenceManagerConfig;

 constructor(config?: Partial<EvidenceManagerConfig>) {
 this.config = {
 maxFileSize: 10 * 1024 * 1024, // 10MB default
 allowedTypes: [
 'application/pdf',
 'application/msword',
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 'image/jpeg',
 'image/png',
 'image/gif'
 ],
 apiEndpoint: '/api/evidence',
 ...config
 };
 }

 /**
 * Validates a file before upload
 */
 validateFile(file: File): { isValid: boolean; error?: string } {
 if (file.size > this.config.maxFileSize) {
 return {
 isValid: false,
 error: `File size exceeds maximum limit of ${this.formatFileSize(this.config.maxFileSize)}`
 };
 }

 if (!this.config.allowedTypes.includes(file.type)) {
 return {
 isValid: false,
 error: `File type ${file.type} is not allowed`
 };
 }

 return { isValid: true };
 }

 /**
 * Uploads evidence for a compliance item
 */
 async uploadEvidence(
 itemId: string,
 file: File,
 description?: string,
 tags?: string[]
 ): Promise<EvidenceUploadResult> {
 try {
 const validation = this.validateFile(file);
 if (!validation.isValid) {
 return { success: false, error: validation.error };
 }

 const formData = new FormData();
 formData.append('file', file);
 formData.append('itemId', itemId);
 if (description) formData.append('description', description);
 if (tags) formData.append('tags', JSON.stringify(tags));

 const response = await fetch(`${this.config.apiEndpoint}/upload`, {
 method: 'POST',
 body: formData,
 });

 if (!response.ok) {
 const errorData = await response.json().catch(() => ({}));
 throw new Error(errorData.message || `Upload failed with status ${response.status}`);
 }

 const result = await response.json();
 return { success: true, evidence: result.evidence };
 } catch (error) {
 return {
 success: false,
 error: error instanceof Error ? error.message : 'Upload failed'
 };
 }
 }

 /**
 * Gets all evidence for a compliance item
 */
 async getEvidence(itemId: string): Promise<Evidence[]> {
 try {
 const response = await fetch(`${this.config.apiEndpoint}?itemId=${itemId}`);
 if (!response.ok) {
 throw new Error(`Failed to fetch evidence: ${response.status}`);
 }

 const data = await response.json();
 return data.evidence || [];
 } catch (error) {
 console.error('Error fetching evidence:', error);
 return [];
 }
 }

 /**
 * Deletes evidence
 */
 async deleteEvidence(evidenceId: string): Promise<boolean> {
 try {
 const response = await fetch(`${this.config.apiEndpoint}/${evidenceId}`, {
 method: 'DELETE',
 });

 return response.ok;
 } catch (error) {
 console.error('Error deleting evidence:', error);
 return false;
 }
 }

 /**
 * Updates evidence metadata
 */
 async updateEvidence(
 evidenceId: string,
 updates: Partial<Pick<Evidence, 'description' | 'tags' | 'status' | 'verificationNotes'>>
 ): Promise<boolean> {
 try {
 const response = await fetch(`${this.config.apiEndpoint}/${evidenceId}`, {
 method: 'PATCH',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(updates),
 });

 return response.ok;
 } catch (error) {
 console.error('Error updating evidence:', error);
 return false;
 }
 }

 /**
 * Downloads evidence file
 */
 async downloadEvidence(evidenceId: string): Promise<{ success: boolean; url?: string; error?: string }> {
 try {
 const response = await fetch(`${this.config.apiEndpoint}/${evidenceId}/download`);
 if (!response.ok) {
 throw new Error(`Download failed: ${response.status}`);
 }

 const blob = await response.blob();
 const url = URL.createObjectURL(blob);
 return { success: true, url };
 } catch (error) {
 return {
 success: false,
 error: error instanceof Error ? error.message : 'Download failed'
 };
 }
 }

 /**
 * Batch upload multiple files
 */
 async uploadMultipleEvidence(
 itemId: string,
 files: File[],
 descriptions?: string[],
 tags?: string[][]
 ): Promise<EvidenceUploadResult[]> {
 const results: EvidenceUploadResult[] = [];

 for (let i = 0; i < files.length; i++) {
 const file = files[i];
 const description = descriptions?.[i];
 const fileTags = tags?.[i];

 const result = await this.uploadEvidence(itemId, file, description, fileTags);
 results.push(result);
 }

 return results;
 }

 /**
 * Gets evidence statistics for an item
 */
 async getEvidenceStats(itemId: string): Promise<{
 total: number;
 verified: number;
 pending: number;
 rejected: number;
 totalSize: number;
 }> {
 try {
 const evidence = await this.getEvidence(itemId);

 return {
 total: evidence.length,
 verified: evidence.filter(e => e.status === 'verified').length,
 pending: evidence.filter(e => e.status === 'pending').length,
 rejected: evidence.filter(e => e.status === 'rejected').length,
 totalSize: evidence.reduce((sum, e) => sum + e.fileSize, 0),
 };
 } catch (error) {
 console.error('Error getting evidence stats:', error);
 return { total: 0, verified: 0, pending: 0, rejected: 0, totalSize: 0 };
 }
 }

 /**
 * Formats file size in human readable format
 */
 formatFileSize(bytes: number): string {
 if (bytes === 0) return '0 Bytes';
 const k = 1024;
 const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
 const i = Math.floor(Math.log(bytes) / Math.log(k));
 return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
 }

 /**
 * Gets file type icon class
 */
 getFileTypeIcon(fileType: string): string {
 const iconMap: Record<string, string> = {
 'application/pdf': 'file-pdf',
 'application/msword': 'file-word',
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'file-word',
 'image/jpeg': 'file-image',
 'image/png': 'file-image',
 'image/gif': 'file-image',
 };

 return iconMap[fileType] || 'file-generic';
 }

 /**
 * Creates a URL for previewing evidence (if supported)
 */
 async getPreviewUrl(evidenceId: string): Promise<string | null> {
 try {
 const response = await fetch(`${this.config.apiEndpoint}/${evidenceId}/preview`);
 if (response.ok) {
 const data = await response.json();
 return data.previewUrl;
 }
 } catch (error) {
 console.error('Error getting preview URL:', error);
 }
 return null;
 }
}

// Default instance
export const evidenceManager = new EvidenceManager();
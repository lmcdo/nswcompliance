import { EvidenceManager, Evidence } from '@/lib/evidence-manager';

// Mock fetch
global.fetch = jest.fn();

describe('EvidenceManager', () => {
 let evidenceManager: EvidenceManager;
 const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

 beforeEach(() => {
 evidenceManager = new EvidenceManager();
 jest.clearAllMocks();
 });

 describe('validateFile', () => {
 test('validates file size correctly', () => {
 const validFile = new File(['small'], 'small.pdf', { type: 'application/pdf' });
 const result = evidenceManager.validateFile(validFile);
 expect(result.isValid).toBe(true);
 });

 test('rejects oversized files', () => {
 const oversizedFile = new File([new ArrayBuffer(20 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' });
 const result = evidenceManager.validateFile(oversizedFile);
 expect(result.isValid).toBe(false);
 expect(result.error).toContain('exceeds maximum limit');
 });

 test('rejects invalid file types', () => {
 const invalidFile = new File(['content'], 'test.exe', { type: 'application/x-executable' });
 const result = evidenceManager.validateFile(invalidFile);
 expect(result.isValid).toBe(false);
 expect(result.error).toContain('not allowed');
 });
 });

 describe('uploadEvidence', () => {
 test('uploads file successfully', async () => {
 const mockEvidence: Evidence = {
 id: '123',
 itemId: 'item1',
 filename: 'test.pdf',
 originalName: 'test.pdf',
 fileType: 'application/pdf',
 fileSize: 1024,
 uploadDate: '2025-01-01',
 uploadedBy: 'user1',
 status: 'pending'
 };

 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({ evidence: mockEvidence })
 });

 const result = await evidenceManager.uploadEvidence('item1', mockFile);

 expect(result.success).toBe(true);
 expect(result.evidence).toEqual(mockEvidence);
 expect(fetch).toHaveBeenCalledWith('/api/evidence/upload', {
 method: 'POST',
 body: expect.any(FormData)
 });
 });

 test('handles upload failure', async () => {
 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: false,
 status: 500,
 json: () => Promise.resolve({ message: 'Server error' })
 });

 const result = await evidenceManager.uploadEvidence('item1', mockFile);

 expect(result.success).toBe(false);
 expect(result.error).toContain('Server error');
 });

 test('validates file before upload', async () => {
 const invalidFile = new File(['content'], 'test.exe', { type: 'application/x-executable' });
 const result = await evidenceManager.uploadEvidence('item1', invalidFile);

 expect(result.success).toBe(false);
 expect(result.error).toContain('not allowed');
 expect(fetch).not.toHaveBeenCalled();
 });
 });

 describe('getEvidence', () => {
 test('fetches evidence successfully', async () => {
 const mockEvidence: Evidence[] = [
 {
 id: '1',
 itemId: 'item1',
 filename: 'test1.pdf',
 originalName: 'test1.pdf',
 fileType: 'application/pdf',
 fileSize: 1024,
 uploadDate: '2025-01-01',
 uploadedBy: 'user1',
 status: 'verified'
 }
 ];

 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({ evidence: mockEvidence })
 });

 const evidence = await evidenceManager.getEvidence('item1');

 expect(evidence).toEqual(mockEvidence);
 expect(fetch).toHaveBeenCalledWith('/api/evidence?itemId=item1');
 });

 test('handles fetch error gracefully', async () => {
 (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

 const evidence = await evidenceManager.getEvidence('item1');

 expect(evidence).toEqual([]);
 });
 });

 describe('deleteEvidence', () => {
 test('deletes evidence successfully', async () => {
 (fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

 const result = await evidenceManager.deleteEvidence('evidence1');

 expect(result).toBe(true);
 expect(fetch).toHaveBeenCalledWith('/api/evidence/evidence1', { method: 'DELETE' });
 });

 test('handles delete failure', async () => {
 (fetch as jest.Mock).mockResolvedValueOnce({ ok: false });

 const result = await evidenceManager.deleteEvidence('evidence1');

 expect(result).toBe(false);
 });
 });

 describe('formatFileSize', () => {
 test('formats bytes correctly', () => {
 expect(evidenceManager.formatFileSize(0)).toBe('0 Bytes');
 expect(evidenceManager.formatFileSize(1024)).toBe('1 KB');
 expect(evidenceManager.formatFileSize(1024 * 1024)).toBe('1 MB');
 expect(evidenceManager.formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
 });
 });

 describe('getFileTypeIcon', () => {
 test('returns correct icons for file types', () => {
 expect(evidenceManager.getFileTypeIcon('application/pdf')).toBe('file-pdf');
 expect(evidenceManager.getFileTypeIcon('image/jpeg')).toBe('file-image');
 expect(evidenceManager.getFileTypeIcon('unknown/type')).toBe('file-generic');
 });
 });

 describe('uploadMultipleEvidence', () => {
 test('uploads multiple files', async () => {
 const mockEvidence: Evidence = {
 id: '123',
 itemId: 'item1',
 filename: 'test.pdf',
 originalName: 'test.pdf',
 fileType: 'application/pdf',
 fileSize: 1024,
 uploadDate: '2025-01-01',
 uploadedBy: 'user1',
 status: 'pending'
 };

 (fetch as jest.Mock).mockResolvedValue({
 ok: true,
 json: () => Promise.resolve({ evidence: mockEvidence })
 });

 const files = [mockFile, mockFile];
 const results = await evidenceManager.uploadMultipleEvidence('item1', files);

 expect(results).toHaveLength(2);
 expect(results[0].success).toBe(true);
 expect(results[1].success).toBe(true);
 expect(fetch).toHaveBeenCalledTimes(2);
 });
 });

 describe('getEvidenceStats', () => {
 test('calculates statistics correctly', async () => {
 const mockEvidence: Evidence[] = [
 {
 id: '1',
 itemId: 'item1',
 filename: 'test1.pdf',
 originalName: 'test1.pdf',
 fileType: 'application/pdf',
 fileSize: 1024,
 uploadDate: '2025-01-01',
 uploadedBy: 'user1',
 status: 'verified'
 },
 {
 id: '2',
 itemId: 'item1',
 filename: 'test2.pdf',
 originalName: 'test2.pdf',
 fileType: 'application/pdf',
 fileSize: 2048,
 uploadDate: '2025-01-01',
 uploadedBy: 'user1',
 status: 'pending'
 }
 ];

 (fetch as jest.Mock).mockResolvedValueOnce({
 ok: true,
 json: () => Promise.resolve({ evidence: mockEvidence })
 });

 const stats = await evidenceManager.getEvidenceStats('item1');

 expect(stats.total).toBe(2);
 expect(stats.verified).toBe(1);
 expect(stats.pending).toBe(1);
 expect(stats.rejected).toBe(0);
 expect(stats.totalSize).toBe(3072);
 });
 });
});
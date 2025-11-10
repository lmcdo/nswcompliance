import { NextApiRequest, NextApiResponse } from 'next';
import { IncomingForm, File } from 'formidable';
import { promises as fs } from 'fs';
import path from 'path';
import { Evidence } from '@/lib/evidence-manager';

export const config = {
 api: {
 bodyParser: false,
 },
};

// Allowed file types
const ALLOWED_TYPES = [
 'application/pdf',
 'application/msword',
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 'image/jpeg',
 'image/png',
 'image/gif'
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const uploadEvidence = async (req: NextApiRequest): Promise<Evidence> => {
 return new Promise((resolve, reject) => {
 const form = new IncomingForm({
 maxFileSize: MAX_FILE_SIZE,
 uploadDir: path.join(process.cwd(), 'uploads', 'evidence'),
 keepExtensions: true,
 });

 // Ensure upload directory exists
 fs.mkdir(form.uploadDir, { recursive: true }).catch(() => {});

 form.parse(req, async (err, fields, files) => {
 if (err) {
 reject(new Error(`Upload failed: ${err.message}`));
 return;
 }

 const file = Array.isArray(files.file) ? files.file[0] : files.file;
 const itemId = Array.isArray(fields.itemId) ? fields.itemId[0] : fields.itemId;
 const description = Array.isArray(fields.description) ? fields.description[0] : fields.description;
 const tags = fields.tags ? JSON.parse(Array.isArray(fields.tags) ? fields.tags[0] : fields.tags) : [];

 if (!file || !itemId) {
 reject(new Error('Missing file or itemId'));
 return;
 }

 // Validate file type
 if (!ALLOWED_TYPES.includes(file.mimetype || '')) {
 reject(new Error(`File type ${file.mimetype} not allowed`));
 return;
 }

 // Validate file size
 if (file.size > MAX_FILE_SIZE) {
 reject(new Error(`File size exceeds maximum limit of ${MAX_FILE_SIZE} bytes`));
 return;
 }

 try {
 // Generate unique filename
 const timestamp = Date.now();
 const randomId = Math.random().toString(36).substr(2, 9);
 const ext = path.extname(file.originalFilename || '');
 const filename = `${timestamp}_${randomId}${ext}`;
 const newPath = path.join(form.uploadDir, filename);

 // Move file to final location
 await fs.rename(file.filepath, newPath);

 // Create evidence record
 const evidence: Evidence = {
 id: `evidence_${timestamp}_${randomId}`,
 itemId: itemId as string,
 filename,
 originalName: file.originalFilename || 'unknown',
 fileType: file.mimetype || 'application/octet-stream',
 fileSize: file.size,
 uploadDate: new Date().toISOString(),
 uploadedBy: 'current_user', // In real app, get from session
 description: description as string,
 tags: tags as string[],
 status: 'pending'
 };

 // In a real implementation, save to database
 console.log('Evidence uploaded:', evidence);

 resolve(evidence);
 } catch (error) {
 reject(new Error(`Failed to process upload: ${error}`));
 }
 });
 });
};

export default async function handler(
 req: NextApiRequest,
 res: NextApiResponse
) {
 if (req.method !== 'POST') {
 res.setHeader('Allow', ['POST']);
 return res.status(405).json({ error: `Method ${req.method} not allowed` });
 }

 try {
 const evidence = await uploadEvidence(req);

 res.status(200).json({
 success: true,
 evidence,
 message: 'File uploaded successfully'
 });
 } catch (error) {
 console.error('Evidence upload error:', error);
 res.status(500).json({
 success: false,
 error: error instanceof Error ? error.message : 'Upload failed',
 });
 }
}
/**
 * QR code generation for PDF reports.
 * Generates a base64 PNG data URL for embedding in @react-pdf/renderer.
 */

import QRCode from 'qrcode';

/**
 * Generate a QR code as a base64-encoded PNG string (no data URI prefix).
 * Returns null on failure — callers should treat QR as optional.
 */
export async function generateQRBase64(url: string): Promise<string | null> {
  try {
    const dataUrl = await QRCode.toDataURL(url, {
      width: 150,
      margin: 1,
      color: { dark: '#111827', light: '#ffffff' },
      errorCorrectionLevel: 'M',
    });
    // Strip "data:image/png;base64," prefix — QRBlock adds it back
    return dataUrl.replace(/^data:image\/png;base64,/, '');
  } catch (err) {
    console.error('[qr] QR code generation failed:', err);
    return null;
  }
}

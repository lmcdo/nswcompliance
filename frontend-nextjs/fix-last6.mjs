import dotenv from 'dotenv';
import pg from 'pg';
import Anthropic from '@anthropic-ai/sdk';
dotenv.config({ path: '.env.local' });

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const R2 = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';

const ids = [86337, 86706, 86429, 79139, 86430, 86418];
for (const id of ids) {
  const r = await pool.query('SELECT id, pdf_page_image_url, v2_heritage_element FROM regulatory_provisions WHERE id = $1', [id]);
  const prov = r.rows[0];
  const elements = prov.v2_heritage_element || [];
  const imageUrl = R2 + prov.pdf_page_image_url;
  const resp = await fetch(imageUrl);
  const buf = await resp.arrayBuffer();
  const b64 = Buffer.from(buf).toString('base64');
  const ctx = elements.length > 0 ? elements.join(', ') : 'heritage';
  const msg = await anthropic.messages.create({
    model: 'claude-3-haiku-20240307', max_tokens: 4000,
    messages: [{ role: 'user', content: [
      { type: 'image', source: { type: 'base64', media_type: 'image/png', data: b64 } },
      { type: 'text', text: `Extract ALL the specific heritage provision control text from this DCP page related to ${ctx}. Include COMPLETE text - do not truncate or summarize. Output the full provision text only.` }
    ]}]
  });
  const text = msg.content[0].text.trim();
  await pool.query('UPDATE regulatory_provisions SET provision_text = $1 WHERE id = $2', [text, id]);
  console.log(`ID ${id}: updated ${text.length} chars`);
}
await pool.end();
console.log('Done');

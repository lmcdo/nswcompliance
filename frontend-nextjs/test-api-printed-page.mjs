import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const API_URL = 'http://localhost:3000/api/provisions/for-property';

const response = await fetch(`${API_URL}?address=45%20Victoria%20Road%20Marrickville&lga=Inner%20West&heritage=true&former_council=Marrickville`);
const data = await response.json();

console.log('API Response for 45 Victoria Road Marrickville:\n');

const heritageProvisions = data.provisions?.heritage || [];
console.log(`Total heritage provisions: ${heritageProvisions.length}`);

// Check first 5 provisions
const sample = heritageProvisions.slice(0, 5);
console.log('\nSample provisions:');
sample.forEach(p => {
  console.log(`ID ${p.id} | pdf_page=${p.pdf_page} | pdf_printed_page=${p.pdf_printed_page} | topic=${p.v2_topic}`);
});

import fetch from 'node-fetch';

async function testAddresses() {
  const addresses = [
    '50 Balmain Road, Leichhardt NSW 2040',
    '18 Sydenham Road, Marrickville NSW 2204',
    '1 Holden Street, Ashfield NSW 2131'
  ];
  
  for (const address of addresses) {
    console.log('\n=== Testing: ' + address + ' ===\n');
    
    try {
      const response = await fetch('http://localhost:3000/api/sepp/structured-requirements?address=' + encodeURIComponent(address));
      const data = await response.json();
      
      if (data.requirements && data.requirements.length > 0) {
        console.log('Total requirements:', data.requirements.length);
        
        // Look for precinct info in first few requirements
        data.requirements.slice(0, 3).forEach((req, i) => {
          console.log('\n[' + (i+1) + '] ' + req.title);
          console.log('    SEPP:', req.seppId);
          if (req.precinct_id) console.log('    Precinct ID:', req.precinct_id);
          if (req.neighbourhood) console.log('    Neighbourhood:', req.neighbourhood);
          if (req.area) console.log('    Area:', req.area);
          if (req.metadata) {
            const meta = typeof req.metadata === 'string' ? JSON.parse(req.metadata) : req.metadata;
            if (meta.precinct) console.log('    Metadata precinct:', meta.precinct);
            if (meta.neighbourhood) console.log('    Metadata neighbourhood:', meta.neighbourhood);
          }
        });
      } else {
        console.log('No requirements found');
      }
      
    } catch (error) {
      console.error('Error:', error.message);
    }
  }
}

testAddresses();

/**
 * Inner West Council Former Council Area Mapping
 *
 * Determines which former council (Ashfield, Leichhardt, Marrickville)
 * a property belongs to based on postcode and suburb name
 */

const postcodeMapping: { [key: string]: string } = {
  // Ashfield postcodes
  '2131': 'Ashfield', // Ashfield
  '2044': 'Ashfield', // St Peters (part)
  '2039': 'Ashfield', // Rozelle (part)
  '2140': 'Ashfield', // Croydon
  '2137': 'Ashfield', // Burwood Heights
  '2133': 'Ashfield', // Croydon Park
  '2132': 'Ashfield', // Enfield
  '2045': 'Ashfield', // Haberfield

  // Leichhardt postcodes
  '2040': 'Leichhardt', // Leichhardt
  '2041': 'Leichhardt', // Balmain
  '2042': 'Leichhardt', // Enmore
  '2043': 'Leichhardt', // Erskineville
  '2038': 'Leichhardt', // Annandale
  '2037': 'Leichhardt', // Glebe
  '2050': 'Leichhardt', // Camperdown
  '2049': 'Leichhardt', // Lewisham

  // Marrickville postcodes
  '2204': 'Marrickville', // Marrickville
  '2048': 'Marrickville', // Stanmore
  '2046': 'Marrickville', // Petersham
  '2047': 'Marrickville', // Dulwich Hill
  '2203': 'Marrickville', // Dulwich Hill (part)
};

const suburbMapping: { [key: string]: string } = {
  // Ashfield suburbs (actual Inner West, not Canada Bay)
  'ashfield': 'Ashfield',
  'croydon': 'Ashfield',
  'croydon park': 'Ashfield',
  'enfield': 'Ashfield',
  'haberfield': 'Ashfield',
  'summer hill': 'Ashfield',
  'five dock': 'Ashfield',
  'wareemba': 'Ashfield',
  'rodd point': 'Ashfield',

  // Leichhardt suburbs
  'leichhardt': 'Leichhardt',
  'balmain': 'Leichhardt',
  'balmain east': 'Leichhardt',
  'birchgrove': 'Leichhardt',
  'rozelle': 'Leichhardt',
  'annandale': 'Leichhardt',
  'glebe': 'Leichhardt',
  'forest lodge': 'Leichhardt',
  'camperdown': 'Leichhardt',
  'newtown': 'Leichhardt',
  'enmore': 'Leichhardt',
  'erskineville': 'Leichhardt',
  'lewisham': 'Leichhardt',

  // Marrickville suburbs
  'marrickville': 'Marrickville',
  'dulwich hill': 'Marrickville',
  'petersham': 'Marrickville',
  'stanmore': 'Marrickville',
  'sydenham': 'Marrickville',
  'tempe': 'Marrickville',
};

/**
 * Determines former Inner West council area from address string
 * @param address - Full address string (e.g., "30 ILLAWARRA ROAD MARRICKVILLE 2204")
 * @param lga - LGA name (must be "INNER WEST" or include "inner west")
 * @returns Former council area name or null if not in Inner West
 */
export function determineFormerCouncilArea(address: string, lga: string): string | null {
  // Only works for Inner West LGA
  if (!lga?.toLowerCase().includes('inner west')) {
    return null;
  }

  const addressLower = address.toLowerCase();

  // First try postcode matching (most reliable)
  const postcodeMatch = addressLower.match(/\b(\d{4})\b/);
  if (postcodeMatch) {
    const postcode = postcodeMatch[1];
    if (postcodeMapping[postcode]) {
      return postcodeMapping[postcode];
    }
  }

  // Then try suburb name matching
  for (const [suburb, councilArea] of Object.entries(suburbMapping)) {
    if (addressLower.includes(suburb)) {
      return councilArea;
    }
  }

  // Unable to determine - return null
  return null;
}
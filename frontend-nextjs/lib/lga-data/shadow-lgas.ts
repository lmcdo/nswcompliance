export interface ShadowLgaData {
  name: string
  slug: string
  heritageCount: number
  densityNote: string
  faqs: Array<{ q: string; a: string }>
}

export const SHADOW_LGAS: ShadowLgaData[] = [
  {
    name: 'Inner West',
    slug: 'inner-west',
    heritageCount: 2039,
    densityNote: 'Medium-to-high density terraces and 3-4 storey apartments create significant shadow exposure on narrow lots.',
    faqs: [
      { q: 'Is shadow a risk in the Inner West?', a: 'Yes -- the Inner West is one of the highest-risk LGAs for shadow in NSW. Narrow lot widths and increasing density of multi-storey development mean adjoining properties can experience substantial winter shadow from new construction.' },
      { q: 'What causes shadow issues in the Inner West?', a: 'The main sources are terrace houses with rear extensions, new 3-4 storey apartment buildings on narrow lots, and dual-occupancy infill. North-facing rear yards are particularly vulnerable to shadow from neighbouring development.' },
      { q: 'Can I object to a DA based on shadow impact in the Inner West?', a: 'Yes. Shadow diagrams are a required part of any DA that could affect neighbouring solar access. Under the Inner West DCP, applicants must demonstrate solar access to north-facing windows and principal outdoor space of adjoining properties. A shadow analysis report prepared by a certifier can support your objection.' },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    heritageCount: 274,
    densityNote: 'A high rate of dual-occupancy and terrace-style infill on standard suburban lots creates shadow risk in established streets.',
    faqs: [
      { q: 'Is shadow a risk in Canterbury-Bankstown?', a: 'Shadow risk is moderate to high in Canterbury-Bankstown. The LGA has high rates of dual-occupancy and new multi-dwelling construction in established suburbs, where new 2-storey buildings can cast significant winter shadows across neighbouring north-facing yards.' },
      { q: 'What causes shadow issues in Canterbury-Bankstown?', a: 'Dual-occupancy developments, terrace-style infill housing, and secondary dwelling additions are the most common sources. Many lots in Campsie, Belmore, and Punchbowl are subject to medium-density uplift under the LEP, increasing the frequency of taller neighbouring builds.' },
      { q: 'What should I check about shadow before buying in Canterbury-Bankstown?', a: 'Check whether neighbouring properties are dual-occupancy eligible and look at the zoning around your lot. If a neighbouring R2 lot is large enough for dual-occupancy, a future two-storey build there could affect your solar access. The shadow tool above runs a seasonal analysis using your specific address.' },
    ],
  },
  {
    name: 'Parramatta',
    slug: 'parramatta',
    heritageCount: 803,
    densityNote: 'Rapid high-rise apartment development in the CBD and medium-density infill across suburban precincts create layered shadow risks across the LGA.',
    faqs: [
      { q: 'Is shadow a risk in Parramatta?', a: 'Shadow risk is high in Parramatta, particularly near the CBD and transport corridors. High-rise towers in the Parramatta CBD cast large winter shadows over a wide area. Suburban precincts see medium-density infill that affects lower-rise neighbours.' },
      { q: 'What causes shadow issues in Parramatta?', a: 'The primary causes are high-rise apartment towers in the CBD precinct, medium-density townhouse and villa development in R3 and R4 zones, and secondary dwelling additions in R2 suburbs. Parramatta\'s urban transformation precincts in Telopea and Carter Street are also active.' },
      { q: 'Can new apartment towers in Parramatta affect my shadow?', a: 'Yes, potentially over a wide radius. Towers taller than 6 storeys can cast winter shadows more than 50m. If you live within 100-200m of a high-rise DA site, a professional shadow analysis using the proposed building height and your property coordinates is worth commissioning.' },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    heritageCount: 131,
    densityNote: 'Large-lot suburban blocks typically provide good separation, but secondary dwelling additions on smaller corner lots create localised shadow risk.',
    faqs: [
      { q: 'Is shadow a risk in Blacktown?', a: 'Shadow risk is lower in Blacktown than in inner Sydney, due to larger lot sizes and lower density. However, secondary dwelling additions and dual-occupancy development on smaller lots can create shadow impacts, particularly where north-facing yards are narrow.' },
      { q: 'What causes shadow issues in Blacktown?', a: 'The main sources are secondary dwelling (granny flat) additions to rear yards, and dual-occupancy development on smaller lots in older suburbs. Two-storey new dwellings on knockdown-rebuild sites can also cast shadow on adjoining single-storey homes.' },
      { q: 'Are secondary dwellings a shadow concern in Blacktown?', a: 'They can be. A granny flat built to the rear of a neighbouring property can affect your north-facing yard if your property is immediately south. The tool above runs a seasonal shadow analysis using the actual position of existing buildings at your address.' },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    heritageCount: 223,
    densityNote: 'Large established homes on sloping terrain create shadow risk on downslope neighbours, particularly in late afternoon on east-west running streets.',
    faqs: [
      { q: 'Is shadow a risk in The Hills Shire?', a: 'Shadow risk in The Hills Shire is moderate. Larger homes on sloping terrain can cast long shadows on downslope properties. Two-storey dwellings are common across the LGA, and while lot sizes are larger than inner Sydney, terrain effects can concentrate shadow impact.' },
      { q: 'What causes shadow issues in The Hills Shire?', a: 'The main causes are large 2-storey homes on elevated lots that cast shadows on lower-lying neighbours, and secondary dwelling additions to rear yards. In growth precincts like Box Hill, new multi-dwelling developments can affect established single-storey neighbours.' },
      { q: 'Does terrain make shadow worse in The Hills Shire?', a: 'Yes in parts of the LGA. Properties on north-facing slopes are generally less affected, but south-facing or east-west running streets can experience shadow earlier in the day from upslope neighbours. The seasonal shadow tool above accounts for actual terrain elevation from satellite data.' },
    ],
  },
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    heritageCount: 956,
    densityNote: 'Low-to-medium density, but coastal hills and stepped terrain cause shadow issues on south-facing slopes.',
    faqs: [
      { q: 'Is shadow a risk on the Northern Beaches?', a: 'Shadow risk on the Northern Beaches is moderate, with terrain being a significant factor. Coastal headlands and hillside topography mean that north-facing properties on south-facing slopes receive excellent light, but properties on north-facing slopes can be unexpectedly shadowed by neighbours on higher ground.' },
      { q: 'What causes shadow issues on the Northern Beaches?', a: 'Terrain is the most significant factor -- elevated homes on hillside blocks cast long shadows on downslope properties. Dual-occupancy and secondary dwelling additions in Dee Why, Brookvale, and Narrabeen also contribute. Heritage-affected areas like Manly and Avalon limit the most disruptive density changes.' },
      { q: 'Does heritage protection reduce shadow risk on the Northern Beaches?', a: 'Partially. Heritage conservation areas in Manly, Avalon, and Palm Beach limit demolition and replacement with larger buildings, which reduces the risk of new high-impact shadow sources in those precincts. Outside conservation areas, standard R2 development controls apply.' },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    heritageCount: 769,
    densityNote: 'Mature tree canopy and 2-storey dwellings on moderately sloping blocks are the primary shadow sources -- terrain and vegetation both matter.',
    faqs: [
      { q: 'Is shadow a risk in Hornsby Shire?', a: 'Shadow risk in Hornsby is moderate. The combination of mature tree canopy, sloping terrain, and 2-storey dwellings means many properties experience more shadow than in flat suburban areas. Secondary dwelling additions and dual-occupancy development are less frequent than in inner Sydney but do occur.' },
      { q: 'What causes shadow issues in Hornsby?', a: 'Established trees are the most common shadow source -- large neighbours\' trees can shade north-facing windows and solar panels. Two-storey homes on upslope lots are the second major source. New medium-density development near Hornsby and Waitara stations is an emerging issue.' },
      { q: 'Can I do anything about neighbouring trees causing shadow in Hornsby?', a: 'Tree removal in Hornsby Shire requires a DA or tree permit in most cases due to the council\'s significant tree register. If a neighbour\'s tree is causing shadow, you can raise it with the council but removal is not guaranteed. The shadow tool above does not model individual trees -- it models buildings only.' },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    heritageCount: 1046,
    densityNote: 'Large established trees and 2-storey dwellings on sloping blocks are the main shadow sources.',
    faqs: [
      { q: 'Is shadow a risk in Ku-ring-gai?', a: 'Shadow risk in Ku-ring-gai is moderate. The combination of large established trees, 2-storey heritage homes, and sloping terrain means many properties experience more winter shadow than appears from a map. Heritage conservation areas limit the worst density changes but do not eliminate shadow risk from existing buildings.' },
      { q: 'What causes shadow issues in Ku-ring-gai?', a: 'Large established trees in rear yards are a significant source, alongside 2-storey Federation and interwar homes on sloping lots that cast long shadows on lower-lying neighbours. Near station precincts (Gordon, Turramurra), medium-density development creates shadow risk for adjacent single-storey properties.' },
      { q: 'Does Ku-ring-gai\'s heritage status protect against shadow?', a: 'Heritage conservation areas restrict demolition and replacement of heritage items, which limits the risk of a new large building appearing where a single-storey cottage once stood. However, existing large dwellings and trees in conservation areas still cast shadow -- heritage does not address existing shadow sources.' },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    heritageCount: 328,
    densityNote: 'Ongoing medium-density uplift near town centres creates shadow exposure risk for established 1-2 storey homes in adjacent streets.',
    faqs: [
      { q: 'Is shadow a risk in Georges River?', a: 'Shadow risk in Georges River is moderate. Medium-density residential development near Hurstville and Kogarah is ongoing, and established single and two-storey homes near station precincts can be affected by neighbouring development at higher densities.' },
      { q: 'What causes shadow issues in Georges River?', a: 'The main sources are new multi-dwelling and apartment buildings near Hurstville and Kogarah station precincts, dual-occupancy development in established R2 suburbs, and secondary dwelling additions to rear yards. The LGA has been subject to medium-density uplift in certain precincts.' },
      { q: 'Which suburbs in Georges River have the highest shadow risk?', a: 'Properties within 200m of Hurstville, Kogarah, and Mortdale town centres have the highest shadow risk due to medium-density zoning. Suburbs further from stations and in lower-density zones have lower risk. The shadow tool above analyses your specific address against current buildings.' },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    heritageCount: 424,
    densityNote: 'Post-war suburban lots and infill dual-occupancy on standard lot widths create moderate shadow risk in established residential streets.',
    faqs: [
      { q: 'Is shadow a risk in Bayside?', a: 'Shadow risk in Bayside is moderate. Post-war residential suburbs with standard lot widths see infill dual-occupancy and secondary dwelling development that can affect north-facing yards of neighbouring properties.' },
      { q: 'What causes shadow issues in Bayside?', a: 'Dual-occupancy infill and secondary dwelling additions are the main sources in Rockdale, Bexley, and Arncliffe. Properties near the Alexandra Canal precinct may also be affected by commercial and industrial conversion DAs that involve larger structures.' },
      { q: 'Are there specific shadow risks near the foreshore in Bayside?', a: 'Properties near Botany Bay are generally low-lying and flat, which limits the shadow risk from terrain. However, new development near the foreshore can affect solar access if buildings are positioned to the north. The tool above models existing building shadows for your specific address.' },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    heritageCount: 574,
    densityNote: 'Dense terrace streets and east-west running lots mean winter shadow from adjoining 2-storey terraces is a common issue across much of the LGA.',
    faqs: [
      { q: 'Is shadow a risk in Randwick?', a: 'Shadow risk in Randwick is moderate to high. Dense terrace housing in the inner suburbs means many properties have limited north-facing roof area and rear yards that receive significant shadow from adjoining 2-storey buildings in winter. Outer suburbs like Matraville have more generous lot sizes and lower shadow risk.' },
      { q: 'What causes shadow issues in Randwick?', a: 'Adjacent 2-storey terrace and semi-detached homes are the dominant shadow source. East-west running streets mean many lots have neighbours directly to the north. Near Kingsford, new medium-density development also creates shadow risk for adjoining single-storey properties.' },
      { q: 'Is shadow worse in inner or outer Randwick?', a: 'Significantly worse in the inner suburbs (Kensington, Randwick, Coogee). Outer suburbs like Matraville and Little Bay have larger lots and lower-density zoning, with correspondingly lower shadow risk. The tool above runs a site-specific analysis using your actual address.' },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    heritageCount: 633,
    densityNote: 'Tightly packed Victorian and Edwardian terrace streets with narrow lot widths make shadow from adjoining 2-storey buildings a near-universal issue.',
    faqs: [
      { q: 'Is shadow a risk in Waverley?', a: 'Shadow risk in Waverley is high. The LGA has some of the most densely packed Victorian-era terrace housing in Sydney. On narrow lots with 2-storey neighbours to the north, winter shadow on north-facing windows and yards is severe and largely unavoidable.' },
      { q: 'What causes shadow issues in Waverley?', a: 'Adjacent 2-storey terrace and semi-detached homes are the almost universal cause. Waverley\'s compact lot sizes leave little room for solar access once a neighbouring property extends to 2 storeys. Heritage conservation area controls limit new large-scale development but cannot address existing building heights.' },
      { q: 'Can heritage controls help with shadow in Waverley?', a: 'Heritage controls prevent demolition and replacement with larger buildings in conservation areas, which limits new shadow sources appearing. But they do not compel removal or modification of existing heritage buildings that already cast shadow. Protection from future shadow is the main benefit.' },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    heritageCount: 761,
    densityNote: 'Heritage terrace density in Paddington and Double Bay creates endemic shadow risk on narrow north-south lots throughout the inner portion of the LGA.',
    faqs: [
      { q: 'Is shadow a risk in Woollahra?', a: 'Shadow risk in Woollahra is high in the Paddington and Double Bay precincts, and moderate in Bellevue Hill and Rose Bay where larger lots provide more separation. The extreme density of terrace houses in Paddington means many properties have restricted solar access regardless of development activity.' },
      { q: 'What causes shadow issues in Woollahra?', a: 'In Paddington, the dominant cause is the existing heritage terrace housing -- many lots are shadowed by their northern neighbours even without any new development. In Bellevue Hill, large 2-storey homes on elevated lots can cast long shadows on lower-lying properties to the south.' },
      { q: 'Does the Woollahra DCP address shadow in heritage areas?', a: 'Woollahra\'s DCP requires shadow diagrams for DAs that increase building height or bulk. New development must not increase shadow on north-facing windows and principal outdoor space of neighbouring properties beyond DCP thresholds. However, existing heritage buildings are not subject to retrospective shadow controls.' },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    heritageCount: 477,
    densityNote: 'Predominantly single and double-storey suburban homes on moderate lots, with secondary dwelling additions to rear yards being the main localised shadow source.',
    faqs: [
      { q: 'Is shadow a risk in the Sutherland Shire?', a: 'Shadow risk in the Sutherland Shire is low to moderate. Larger suburban lots and predominantly 1-2 storey housing provide reasonable separation. The main shadow risk comes from secondary dwelling additions and new 2-storey knockdown-rebuild projects on properties directly to the north.' },
      { q: 'What causes shadow issues in the Sutherland Shire?', a: 'Secondary dwelling additions to rear yards of neighbouring properties are the most common cause in established suburbs. Knockdown-rebuild projects replacing single-storey homes with 2-storey dwellings also increase shadow on adjoining properties.' },
      { q: 'Are there shadow risks near national parks in the Sutherland Shire?', a: 'Properties near Royal National Park generally have low shadow risk from built development given the adjacent open space. Terrain shadow from bushland ridgelines can be a factor on south-facing slopes but is not related to neighbouring development.' },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    heritageCount: 149,
    densityNote: 'New estate homes on compact lots are increasingly close to one another, with 2-storey designs that can shadow adjoining single-storey neighbours on north-facing aspects.',
    faqs: [
      { q: 'Is shadow a risk in Camden?', a: 'Shadow risk in Camden is moderate and growing as new estates develop. Greenfield estates have compact lot widths where 2-storey homes can shadow adjoining single-storey properties. In established suburbs, the risk is lower due to larger lots and predominantly single-storey housing.' },
      { q: 'What causes shadow issues in Camden?', a: 'In new estates, 2-storey dwellings on narrow lots are the main source. When a neighbour builds 2 storeys on a standard estate lot, north-facing yards and windows of the property to the south can be significantly affected in winter.' },
      { q: 'Are new estate builds subject to shadow controls in Camden?', a: 'Yes. Camden Council\'s DCP requires shadow diagrams for 2-storey dwellings and additions. Applicants must demonstrate that shadow on north-facing windows and principal outdoor space of adjoining properties meets the DCP solar access objective. Check the DA before construction begins.' },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    heritageCount: 97,
    densityNote: 'Mix of established post-war suburbs with moderate shadow risk and new compact-lot estates where 2-storey construction is standard.',
    faqs: [
      { q: 'Is shadow a risk in Liverpool?', a: 'Shadow risk in Liverpool is low to moderate. Established suburbs have larger lots with reasonable separation. In newer estates in Edmondson Park and Carnes Hill, compact lot widths and standard 2-storey designs create moderate shadow risk between neighbouring properties.' },
      { q: 'What causes shadow issues in Liverpool?', a: 'In new estates, standard 2-storey dwellings on compact lots cast winter shadows on adjoining single-storey or lower-storey properties. In established suburbs, secondary dwelling additions are the most common source.' },
      { q: 'Are shadow controls applied to secondary dwellings in Liverpool?', a: 'Secondary dwellings approved as CDCs through private certifiers must comply with the Complying Development Codes under SEPP Housing 2021, which include setback and height controls that indirectly limit shadow. However, CDC applications are not subject to council review of shadow impact on neighbours.' },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    heritageCount: 253,
    densityNote: 'Predominantly single and double-storey suburban homes, with active secondary dwelling and knockdown-rebuild activity introducing new shadow sources in established streets.',
    faqs: [
      { q: 'Is shadow a risk in Penrith?', a: 'Shadow risk in Penrith is low to moderate. Larger lot sizes provide reasonable building separation. The main risk arises from secondary dwelling additions and 2-storey knockdown-rebuild projects in established suburbs where the previous dwelling was single-storey.' },
      { q: 'What causes shadow issues in Penrith?', a: 'Secondary dwelling additions to rear yards, and new 2-storey dwellings on lots where single-storey homes previously stood, are the most common shadow sources. In growth areas, compact-lot estate homes at 2 storeys can also affect adjoining single-storey properties.' },
      { q: 'Is shadow from neighbours worse in Penrith in summer or winter?', a: 'Winter is always worse for shadow -- the sun is lower in the sky, so shadows are longer and more southerly in direction. Penrith\'s high sunshine hours mean the financial impact of losing winter solar access is significant for both solar panels and passive solar heating of the home.' },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    heritageCount: 604,
    densityNote: 'Rural-residential and large-lot suburban properties generally have low shadow risk, but heritage homestead redevelopments in Windsor and Richmond can affect compact heritage streetscapes.',
    faqs: [
      { q: 'Is shadow a risk in Hawkesbury?', a: 'Shadow risk in Hawkesbury is generally low given the predominantly rural-residential character with large lots and low building heights. In the town centres of Windsor and Richmond, heritage conservation areas limit large-scale development that might create shadow, but existing 2-storey heritage buildings can affect adjoining narrow lots.' },
      { q: 'What causes shadow issues in Hawkesbury?', a: 'In rural-residential areas, secondary dwelling additions are the most common shadow source. In Windsor and Richmond, 2-storey heritage commercial and residential buildings in the conservation precincts can shadow adjacent properties on narrow lot widths.' },
      { q: 'Does flooding affect shadow risk considerations in Hawkesbury?', a: 'Indirectly -- flood-affected properties are often required to elevate floor levels, which increases overall building height and can increase shadow cast on neighbouring properties. If a neighbour is rebuilding to a raised floor level after a flood event, the resulting building may be taller than expected.' },
    ],
  },
  {
    name: 'Wollongong',
    slug: 'wollongong',
    heritageCount: 519,
    densityNote: 'The Illawarra escarpment creates terrain shadow on properties to its east, while medium-density development near the CBD creates built shadow in the inner suburbs.',
    faqs: [
      { q: 'Is shadow a risk in Wollongong?', a: 'Shadow risk in Wollongong is moderate. The escarpment causes terrain shadow for some properties in the afternoon, and medium-density development near Wollongong CBD creates built shadow risk. In established suburban areas the risk is low to moderate.' },
      { q: 'What causes shadow issues in Wollongong?', a: 'Terrain shadow from the Illawarra escarpment affects western-facing properties in the afternoon. In the city and inner suburbs, medium-density apartment and townhouse development creates shadow risk for existing single and 2-storey homes. Secondary dwelling CDCs in suburban areas are also a source.' },
      { q: 'Are escarpment-adjacent properties more shadow-affected in Wollongong?', a: 'Properties immediately east of the escarpment can receive reduced afternoon sun during winter when the sun is lower in the sky. This terrain shadow cannot be addressed through the planning system. The shadow tool above models building shadows only -- terrain shadow requires a separate analysis.' },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    heritageCount: 1153,
    densityNote: 'Low building density and large lot sizes mean shadow risk is minimal across most of the LGA, with heritage streetscapes in Grafton and Maclean the main exception.',
    faqs: [
      { q: 'Is shadow a risk in Clarence Valley?', a: 'Shadow risk in Clarence Valley is generally low. Predominantly single-storey buildings on large lots mean shadow from neighbouring development is rarely an issue. The main exception is the Grafton heritage conservation area, where 2-storey commercial and residential buildings on narrow town lots can affect adjoining properties.' },
      { q: 'What causes shadow issues in Clarence Valley?', a: 'In Grafton town centre, 2-storey heritage commercial buildings on narrow lots can shade adjacent properties. In residential areas, shadow risk from neighbouring development is low given large lot sizes and predominantly single-storey construction.' },
      { q: 'Does Clarence Valley\'s high heritage count create shadow complications?', a: 'Not typically for shadow purposes. The 1,153 heritage items in Clarence Valley are spread across a large geographic area and many are rural properties or standalone heritage items. Heritage controls prevent demolition and replacement with larger buildings, which if anything reduces the risk of new shadow sources appearing.' },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    heritageCount: 332,
    densityNote: 'Small-town character with single-storey homes on generous lots means built shadow risk is very low across most of the LGA.',
    faqs: [
      { q: 'Is shadow a risk in Yass Valley?', a: 'Shadow risk in Yass Valley is very low. Single-storey buildings on large lots dominate across the LGA. Built shadow from neighbouring development is rarely a significant concern outside the Yass town centre compact streets.' },
      { q: 'What causes shadow issues in Yass Valley?', a: 'In Yass town, 2-storey buildings on compact heritage streetscapes can shade adjoining narrow lots. In rural-residential and suburban areas, the generous lot sizes and single-storey construction mean shadow is generally not a planning consideration.' },
      { q: 'Are there terrain shadow issues in Yass Valley?', a: 'Yass Valley has rolling terrain, and some rural properties on south-facing slopes receive reduced winter sun. This is a site assessment question rather than a planning one -- the shadow tool above models building shadows, not terrain, but the BOM sunshine hours figure used in the solar check accounts for local climate.' },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    heritageCount: 168,
    densityNote: 'Flat rural town character with generous lot sizes means shadow from neighbouring buildings is rarely an issue.',
    faqs: [
      { q: 'Is shadow a risk in Forbes?', a: 'Shadow risk in Forbes is very low. The town is predominantly single-storey on large flat lots with generous setbacks. Neighbouring building shadow is rarely a concern for residents or solar installers in Forbes.' },
      { q: 'What causes shadow issues in Forbes?', a: 'Secondary dwelling additions on compact town lots are the most common shadow source, though even these are infrequent. In the Forbes town centre, a small number of 2-storey commercial buildings can affect narrow adjoining lots.' },
      { q: 'How does Forbes compare to Sydney for shadow risk?', a: 'Forbes is significantly lower risk than Sydney LGAs. The flat terrain, single-storey building character, and large lot sizes mean properties have minimal shadow from neighbouring buildings. The main solar concern in Forbes is maximising output from excellent sunshine hours, not managing shadow.' },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    heritageCount: 513,
    densityNote: 'Regional city with standard suburban density -- 2-storey homes in residential subdivision create moderate shadow risk on adjoining standard lots.',
    faqs: [
      { q: 'Is shadow a risk in Tamworth Regional?', a: 'Shadow risk in Tamworth is low to moderate. Standard suburban density with 2-storey homes on typical residential lots creates some shadow risk between neighbours, but the generous lot sizes and flat to gently sloping terrain keep overall risk lower than coastal cities.' },
      { q: 'What causes shadow issues in Tamworth Regional?', a: '2-storey dwellings on standard residential lots are the main source, along with secondary dwelling additions in established suburbs. Near the Tamworth CBD, 2-3 storey commercial buildings on the main street can affect narrow adjoining properties.' },
      { q: 'Does Tamworth\'s high sunshine hours offset shadow concerns?', a: 'Partially. Tamworth receives 2,840 sunshine hours per year -- any shadow loss has a higher financial cost than in Sydney because there is more generation to lose. This makes shadow assessment relatively more important for solar installations in Tamworth, not less.' },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    heritageCount: 431,
    densityNote: 'Heritage terrace housing in the city centre and 2-storey suburban homes on standard lots create moderate shadow risk, particularly in heritage precincts on compact lots.',
    faqs: [
      { q: 'Is shadow a risk in Bathurst Regional?', a: 'Shadow risk in Bathurst is low to moderate. Heritage terrace housing in the Bathurst city centre creates localised shadow risk on narrow lots, similar to inner Sydney heritage precincts. Suburban residential areas have larger lots and lower risk.' },
      { q: 'What causes shadow issues in Bathurst Regional?', a: '2-storey heritage buildings in the city centre and Bathurst\'s heritage residential streets create shadow on adjoining narrow lots. In suburban areas, 2-storey dwellings and secondary dwelling additions are the main sources.' },
      { q: 'Does Bathurst\'s heritage conservation area affect shadow analysis?', a: 'Heritage conservation area controls in Bathurst limit demolition and replacement with larger buildings, which prevents new large shadow sources appearing in heritage precincts. However, existing heritage buildings already creating shadow are not affected by these controls. The shadow tool above models existing building shadow for your specific address.' },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    heritageCount: 577,
    densityNote: 'Heritage town centres with 2-storey buildings and rural-residential character with generous separation create a mixed shadow profile across the LGA.',
    faqs: [
      { q: 'Is shadow a risk in Wingecarribee (Southern Highlands)?', a: 'Shadow risk in Wingecarribee is low to moderate. Bowral and Moss Vale town centres have 2-storey heritage buildings on compact lots that can affect adjoining properties. Rural-residential and suburban areas have larger lots with low shadow risk from built development.' },
      { q: 'What causes shadow issues in Wingecarribee?', a: 'In Bowral, 2-storey heritage commercial and residential buildings in the conservation area can shade adjoining narrow lots. In residential areas, 2-storey dwellings and secondary dwelling additions are the main sources. The Southern Highlands\' hilly terrain can also affect afternoon shadow on south-facing slopes.' },
      { q: 'Is shadow more important in Wingecarribee given the lower sunshine hours?', a: 'Yes. Wingecarribee receives around 2,350 sunshine hours per year -- the lowest of the LGAs in this analysis. Any shadow loss reduces an already lower solar resource. If solar panels are a priority, minimising shadow from neighbouring buildings is particularly important before installation.' },
    ],
  },
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    heritageCount: 116,
    densityNote: 'Established suburban areas have moderate lot sizes, while new release estates with compact lots and 2-storey designs create shadow between neighbouring properties.',
    faqs: [
      { q: 'Is shadow a risk in Campbelltown?', a: 'Shadow risk in Campbelltown is low to moderate. Established suburbs have larger lots with good separation. In newer estates and growth areas like Menangle Park, compact lot widths with standard 2-storey designs create moderate shadow risk between neighbours.' },
      { q: 'What causes shadow issues in Campbelltown?', a: 'In new estates, 2-storey dwellings on compact lots are the main source. In established suburbs, secondary dwelling additions and knockdown-rebuild projects replacing single-storey homes with 2-storey designs increase shadow on adjoining properties.' },
      { q: 'Are new estates in Campbelltown subject to shadow controls?', a: 'Yes. Campbelltown DCP requires shadow diagrams for 2-storey dwellings and additions. Applicants must demonstrate solar access to north-facing windows and principal outdoor space of adjoining properties.' },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    heritageCount: 287,
    densityNote: 'Medium-density transition near Lane Cove town centre creates shadow risk for established single-storey homes on adjacent streets.',
    faqs: [
      { q: 'Is shadow a risk in Lane Cove?', a: 'Shadow risk in Lane Cove is moderate. The LGA is transitioning to medium density near the town centre and along the Pacific Highway. New 3-4 storey apartment buildings can cast significant shadow on adjoining lower-density properties.' },
      { q: 'What causes shadow issues in Lane Cove?', a: 'Medium-density apartment and townhouse development near Lane Cove town centre is the primary source. Properties near Lane Cove National Park have low built shadow risk due to adjacent open space.' },
      { q: 'Does the medium-density transition affect shadow in Lane Cove?', a: 'Yes. Properties at the interface between R2 and R3/R4 zones are most at risk. A 3-4 storey building on a neighbouring R3 lot can significantly shadow an adjoining R2 property.' },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    heritageCount: 412,
    densityNote: 'High-density development near Macquarie Park and Top Ryde creates shadow risk for established suburban homes in adjacent streets.',
    faqs: [
      { q: 'Is shadow a risk in Ryde?', a: 'Shadow risk in Ryde is moderate to high near Macquarie Park and Top Ryde, where high-density apartment development is ongoing. Established suburban areas further from centres have lower risk.' },
      { q: 'What causes shadow issues in Ryde?', a: 'High-rise towers in Macquarie Park and medium-density development near Top Ryde are the main sources. In established suburbs, knockdown-rebuild projects and secondary dwelling additions also contribute.' },
      { q: 'Can Macquarie Park towers affect shadow on nearby homes?', a: 'Yes. Towers can cast long winter shadows. Properties within 100-200m, particularly to the south, can experience reduced solar access. Check the DA register for proposed developments near your address.' },
    ],
  },
  {
    name: 'Blue Mountains',
    slug: 'blue-mountains',
    heritageCount: 489,
    densityNote: 'Heritage village character with single-storey cottages, but steep terrain and mature canopy create natural shadow. New 2-storey builds on sloping lots are the main built shadow risk.',
    faqs: [
      { q: 'Is shadow a risk in the Blue Mountains?', a: 'Shadow risk from built development is low to moderate. Village character and heritage controls limit large-scale development. However, steep terrain and dense tree canopy create significant natural shadow, particularly on south-facing slopes in winter.' },
      { q: 'What causes shadow issues in the Blue Mountains?', a: 'Terrain and tree canopy are the dominant shadow sources. Where built shadow occurs, it is typically from 2-storey dwellings on elevated lots. New builds replacing single-storey cottages with 2-storey designs also create localised impact.' },
      { q: 'Does heritage village character limit shadow risk?', a: 'Partially. Heritage conservation areas in Leura, Katoomba, and Wentworth Falls restrict demolition and replacement with larger buildings. However, not all areas are heritage-protected.' },
    ],
  },
  {
    name: 'Shoalhaven',
    slug: 'shoalhaven',
    heritageCount: 387,
    densityNote: 'Predominantly single-storey coastal and rural-residential character with low built shadow risk, but terrain shadow on hillside lots near Nowra and Berry.',
    faqs: [
      { q: 'Is shadow a risk in Shoalhaven?', a: 'Shadow risk in Shoalhaven is generally low. Single-storey homes on larger lots dominate. Some terrain shadow occurs on hillside lots near Nowra and Berry where sloping blocks create elevation differences between neighbours.' },
      { q: 'What causes shadow issues in Shoalhaven?', a: 'Terrain is more significant than built form. In Nowra and Berry, sloping lots mean uphill properties can cast shadow on downslope neighbours. Secondary dwelling additions and 2-storey rebuilds on coastal village lots are the main built shadow sources.' },
      { q: 'Does the coastal character limit shadow risk?', a: 'Yes. Most South Coast villages have low-density character with generous lot sizes and predominantly single-storey buildings.' },
    ],
  },
]

export const SHADOW_LGA_SLUG_MAP: Record<string, ShadowLgaData> = Object.fromEntries(
  SHADOW_LGAS.map(lga => [lga.slug, lga])
)

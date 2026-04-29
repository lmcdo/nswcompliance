// Financial constants — must match SolarYieldTool.tsx
const RETAIL_RATE        = 0.32
const FEED_IN_RATE       = 0.06
const SELF_CONSUME_RATIO = 0.30
const COST_PER_WATT      = 1.00
const PANEL_WATTS        = 400
const INVERTER_REPLACE   = 2000
const REF_PANELS         = 16.5  // 6.6 kW reference system

function refPayback(sunshineHours: number): string {
  const annualKwh = sunshineHours * 6.6 * 0.8
  const saving = annualKwh * SELF_CONSUME_RATIO * RETAIL_RATE + annualKwh * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE
  const cost = (REF_PANELS * PANEL_WATTS / 1000) * 1000 * COST_PER_WATT
  const payback = cost / saving
  return payback.toFixed(1)
}

export interface SolarLgaData {
  name: string
  slug: string
  sunshineHoursPerYear: number
  bomStation: string
  heritageCount: number
  /** Computed payback for a reference 6.6 kW system */
  refPaybackYears: string
  faqs: Array<{ q: string; a: string }>
}

export const SOLAR_LGAS: SolarLgaData[] = [
  {
    name: 'Inner West',
    slug: 'inner-west',
    sunshineHoursPerYear: 2500,
    bomStation: 'Sydney Observatory Hill',
    heritageCount: 2039,
    refPaybackYears: refPayback(2500),
    faqs: [
      { q: 'Is solar worth it in the Inner West?', a: `The Inner West receives around 2,500 sunshine hours per year (BOM Observatory Hill station). A reference 6.6 kW system yields roughly ${Math.round(2500 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2500)} years at current NSW tariffs. North-facing roofs above 15° pitch achieve the best return.` },
      { q: 'Does heritage listing affect solar panels in the Inner West?', a: 'The Inner West has 2,039 heritage items and conservation areas. Solar panels on a heritage-listed property or within a heritage conservation area typically require council approval and may face restrictions on panel placement, visibility from the street, and fixing methods. Check your address above before proceeding.' },
      { q: 'What solar rebates are available in the Inner West?', a: 'NSW solar incentives include Small-scale Technology Certificates (STCs) under the federal SRES scheme, which reduce upfront system cost. There are no Inner West Council-specific solar rebates as of 2026. The federal scheme is applicable state-wide.' },
      { q: 'What feed-in tariff can I get in the Inner West?', a: 'Feed-in tariffs in NSW are set by retailers, not mandated by government. The AER voluntary benchmark is around 6¢/kWh. Some retailers offer slightly higher rates for flat-rate plans. Compare using Energy Made Easy (energymadeeasy.gov.au) for current offers.' },
      { q: 'How much roof area do I need for solar in the Inner West?', a: 'A 6.6 kW system (16-17 panels at 400W each) requires approximately 26–28 m² of usable north-facing roof area. The Inner West has a mix of terrace houses and semi-detached homes — the aerial imagery check above estimates your specific usable roof area based on satellite data.' },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 274,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Canterbury-Bankstown?', a: `Canterbury-Bankstown receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years. The area has good solar potential with many north-facing suburban roofs.` },
      { q: 'Are there heritage restrictions on solar in Canterbury-Bankstown?', a: 'Canterbury-Bankstown has 274 heritage items. If your property is a heritage item or in a heritage conservation area, solar panel installation may need council approval. Check your address status with the checker above.' },
      { q: 'What size solar system suits a Canterbury-Bankstown home?', a: 'Most Canterbury-Bankstown homes are suitable for 6.6–10 kW systems. Larger blocks and double-storey homes can accommodate bigger systems. The checker above estimates your specific roof capacity from aerial imagery.' },
      { q: 'What is the average electricity bill saving from solar in Canterbury-Bankstown?', a: `At 2,480 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2480 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2480 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year (AER 2025–26 tariff benchmark, 30% self-consumption).` },
      { q: 'Does the orientation of my Canterbury-Bankstown roof affect solar yield?', a: 'Yes significantly. North-facing roofs produce 10–15% more than east or west, and approximately 30% more than south-facing. The checker above analyses your specific roof orientation from aerial imagery and factors this into the yield estimate.' },
    ],
  },
  {
    name: 'Parramatta',
    slug: 'parramatta',
    sunshineHoursPerYear: 2520,
    bomStation: 'Parramatta',
    heritageCount: 803,
    refPaybackYears: refPayback(2520),
    faqs: [
      { q: 'Is solar worth it in Parramatta?', a: `Parramatta receives around 2,520 sunshine hours per year, slightly above the Sydney average. A 6.6 kW system yields approximately ${Math.round(2520 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2520)} years.` },
      { q: 'Are there heritage restrictions on solar in Parramatta?', a: 'Parramatta has 803 heritage items including significant colonial-era buildings. Solar on a heritage-listed property in Parramatta typically requires a heritage impact assessment and council approval. The Parramatta CBD conservation area has strict controls on visible rooftop modifications.' },
      { q: 'What solar systems suit Parramatta apartments and townhouses?', a: 'Many newer Parramatta townhouses have adequate roof area for 5–10 kW systems. Strata-titled apartments require approval from the owners corporation. Battery storage is increasingly viable in Parramatta given high daytime electricity prices.' },
      { q: 'How much does a solar system cost in Parramatta?', a: `At approximately $1.00/W installed after STCs (SolarQuotes NSW 2026), a 6.6 kW system costs around $6,600 before any additional rebates. The ${refPayback(2520)}-year payback assumes current AER tariff benchmarks.` },
      { q: 'What feed-in tariff applies to Parramatta solar systems?', a: 'Parramatta is served by Endeavour Energy network. Feed-in tariffs are set by your electricity retailer — the AER voluntary benchmark for NSW is around 6¢/kWh. Compare current retailer offers at energymadeeasy.gov.au.' },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    sunshineHoursPerYear: 2550,
    bomStation: 'Richmond',
    heritageCount: 131,
    refPaybackYears: refPayback(2550),
    faqs: [
      { q: 'Is solar worth it in Blacktown?', a: `Blacktown averages around 2,550 sunshine hours per year — above the Sydney CBD average due to its inland location. A 6.6 kW system yields approximately ${Math.round(2550 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2550)} years.` },
      { q: 'What solar systems are common in Blacktown?', a: 'Blacktown\'s predominantly single-storey suburban homes with large north-facing roofs are well-suited to 6.6–13.2 kW systems. Many households in the area have already installed solar, with battery storage uptake growing.' },
      { q: 'Are there heritage restrictions on solar in Blacktown?', a: 'Blacktown has 131 heritage items — relatively few compared to older Sydney suburbs. Heritage-related solar restrictions are unlikely unless your property is specifically heritage-listed.' },
      { q: 'What are average solar savings in Blacktown?', a: `At 2,550 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2550 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2550 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year based on current NSW tariff benchmarks.` },
      { q: 'Which network serves Blacktown for solar feed-in?', a: 'Blacktown is served by Endeavour Energy (formerly part of the Western Power corridor). Your feed-in tariff is set by your electricity retailer — compare at energymadeeasy.gov.au for current offers.' },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    sunshineHoursPerYear: 2580,
    bomStation: 'Richmond',
    heritageCount: 223,
    refPaybackYears: refPayback(2580),
    faqs: [
      { q: 'Is solar worth it in The Hills Shire?', a: `The Hills Shire receives around 2,580 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2580 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2580)} years — among the better payback periods in Greater Sydney.` },
      { q: 'What size solar system suits Hills District homes?', a: 'The Hills Shire has many large single and double-storey homes with ample roof area. Systems of 10–20 kW are common. The checker above estimates your specific roof capacity from aerial imagery.' },
      { q: 'Are there heritage restrictions on solar in The Hills Shire?', a: 'The Hills Shire has 223 heritage items. Most are in village centres (Rouse Hill, Kellyville) rather than residential suburbs. Check your address above if near a heritage conservation area.' },
      { q: 'What network serves The Hills Shire?', a: 'The Hills Shire is served by Endeavour Energy. Feed-in tariffs are set by your retailer — compare at energymadeeasy.gov.au.' },
      { q: 'Is battery storage worth it in The Hills Shire?', a: 'With relatively high sunshine hours and many large homes, The Hills Shire is a good candidate for battery storage. A 10 kWh battery paired with a 10+ kW solar system can increase self-consumption significantly, improving the overall return.' },
    ],
  },
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    sunshineHoursPerYear: 2580,
    bomStation: 'Manly',
    heritageCount: 956,
    refPaybackYears: refPayback(2580),
    faqs: [
      { q: 'Is solar worth it on the Northern Beaches?', a: `The Northern Beaches receives around 2,580 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2580 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2580)} years. Coastal properties may need corrosion-resistant mounting hardware.` },
      { q: 'Are there heritage restrictions on solar on the Northern Beaches?', a: 'Northern Beaches has 956 heritage items. Many beachside villages (Manly, Avalon, Pittwater) have heritage conservation areas. Solar on heritage-listed properties typically requires council approval and may face restrictions on street-visible placement.' },
      { q: 'Does salt air affect solar panels on the Northern Beaches?', a: 'Coastal properties within about 1 km of the ocean should use panels with C5 salt-spray rated mounting systems. Premium panel manufacturers offer marine-grade options. This adds cost but protects against accelerated corrosion.' },
      { q: 'What network serves the Northern Beaches?', a: 'Northern Beaches is served by Ausgrid. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'How much roof area do I need for solar on the Northern Beaches?', a: 'Most Northern Beaches homes are single or double-storey with moderate roof areas. A 6.6 kW system requires 26–28 m² of usable north-facing roof. The checker above estimates your specific capacity from aerial imagery.' },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    sunshineHoursPerYear: 2520,
    bomStation: 'Pennant Hills',
    heritageCount: 769,
    refPaybackYears: refPayback(2520),
    faqs: [
      { q: 'Is solar worth it in Hornsby Shire?', a: `Hornsby Shire receives around 2,520 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2520 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2520)} years. Tree canopy in some areas can reduce effective yield — check shading in the aerial tile above.` },
      { q: 'Are there heritage restrictions on solar in Hornsby?', a: 'Hornsby Shire has 769 heritage items. Several townships have heritage conservation areas including Berowra, Galston, and parts of Hornsby town centre. Solar on listed buildings or in conservation areas requires council approval.' },
      { q: 'Does tree shading affect solar in Hornsby?', a: 'Hornsby\'s heavily treed character means shading is a significant factor for many properties. The aerial imagery analysis checks for roof area but cannot account for nearby tree shading. A site inspection by an installer is recommended to assess shading impact.' },
      { q: 'What network serves Hornsby?', a: 'Hornsby is served by Ausgrid. Feed-in tariffs are negotiated with your electricity retailer.' },
      { q: 'What solar system size suits Hornsby homes?', a: 'Hornsby has a mix of small cottages and larger family homes. System sizes range from 5 kW for smaller blocks to 10–13 kW for larger properties. Use the checker above to estimate your specific roof capacity.' },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    sunshineHoursPerYear: 2490,
    bomStation: 'Ryde',
    heritageCount: 221,
    refPaybackYears: refPayback(2490),
    faqs: [
      { q: 'Is solar worth it in Ryde?', a: `Ryde receives around 2,490 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2490 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2490)} years.` },
      { q: 'Are there heritage restrictions on solar in Ryde?', a: 'Ryde has 221 heritage items. Heritage constraints are mainly in older residential areas of Meadowbank and top of Ryde. Check your address status if near a heritage conservation area.' },
      { q: 'What solar systems suit Ryde homes?', a: 'Ryde has a mix of older homes on large blocks and newer apartments. Standalone homes typically suit 6.6–10 kW systems. The checker above estimates your specific roof capacity.' },
      { q: 'What network serves Ryde?', a: 'Ryde is served by Ausgrid.' },
      { q: 'What are average solar savings in Ryde?', a: `At 2,490 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2490 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2490 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year at current NSW tariffs.` },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    sunshineHoursPerYear: 2490,
    bomStation: 'Ryde',
    heritageCount: 318,
    refPaybackYears: refPayback(2490),
    faqs: [
      { q: 'Is solar worth it in Lane Cove?', a: `Lane Cove receives around 2,490 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2490 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2490)} years. Many Lane Cove homes have north-facing rear roofs well-suited for solar.` },
      { q: 'Are there heritage restrictions on solar in Lane Cove?', a: 'Lane Cove has 318 heritage items, particularly around Lane Cove village and older residential streets. Solar on heritage-listed properties or in conservation areas requires development consent from Lane Cove Council.' },
      { q: 'Does tree canopy affect solar in Lane Cove?', a: 'Lane Cove\'s tree canopy is significant. Shading from neighbouring trees should be assessed before installation. Installers can model shading impacts using the address coordinates.' },
      { q: 'What network serves Lane Cove?', a: 'Lane Cove is served by Ausgrid.' },
      { q: 'What solar system size is typical for Lane Cove homes?', a: 'Lane Cove\'s post-war homes on moderate blocks typically suit 5–10 kW systems. Use the checker above to see your specific roof capacity from aerial imagery.' },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    sunshineHoursPerYear: 2520,
    bomStation: 'Pennant Hills',
    heritageCount: 1046,
    refPaybackYears: refPayback(2520),
    faqs: [
      { q: 'Is solar worth it in Ku-ring-gai?', a: `Ku-ring-gai receives around 2,520 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2520 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2520)} years. Ku-ring-gai\'s large homes often support bigger systems with better returns.` },
      { q: 'Does Ku-ring-gai\'s heritage status affect solar?', a: 'Ku-ring-gai has 1,046 heritage items — one of the highest counts in Sydney. Many streets in Gordon, Killara, Lindfield, and Wahroonga have heritage conservation areas. Solar on properties in conservation areas requires a heritage impact assessment and council approval.' },
      { q: 'Can I install solar on a Ku-ring-gai Federation home?', a: 'Federation-era homes in Ku-ring-gai\'s conservation areas can often have solar installed on rear roof sections not visible from the street. Council approval is required — a heritage consultant can advise on acceptable placement and visual impact.' },
      { q: 'What network serves Ku-ring-gai?', a: 'Ku-ring-gai is served by Ausgrid.' },
      { q: 'What solar system size suits Ku-ring-gai homes?', a: 'Ku-ring-gai\'s large properties frequently suit 10–20 kW systems. Many homes have significant north-facing roof area. Use the checker above to see your exact roof capacity.' },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 328,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Georges River?', a: `Georges River LGA receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years.` },
      { q: 'Are there heritage restrictions on solar in Georges River?', a: 'Georges River has 328 heritage items across suburbs like Hurstville, Kogarah, and Oatley. Heritage conservation areas in Oatley and parts of Hurstville may require approval for solar installation.' },
      { q: 'What solar systems suit Georges River homes?', a: 'Georges River has a mix of post-war homes on moderate blocks. Systems of 5–10 kW are typical. Check your specific roof area using the checker above.' },
      { q: 'What network serves Georges River?', a: 'Georges River is served by Ausgrid.' },
      { q: 'What are average solar savings in Georges River?', a: `At 2,480 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2480 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2480 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year at current NSW tariffs.` },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 424,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Bayside?', a: `Bayside receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years.` },
      { q: 'Are there heritage restrictions on solar in Bayside?', a: 'Bayside has 424 heritage items, particularly in Rockdale and Botany areas. Some interwar suburbs have heritage conservation areas — check your address if near Bexley, Arncliffe, or Rockdale heritage precincts.' },
      { q: 'Does being near the coast affect solar panel longevity in Bayside?', a: 'Properties within about 1 km of Botany Bay should use marine-grade mounting hardware. Premium panel manufacturers offer corrosion-resistant options suitable for coastal environments.' },
      { q: 'What network serves Bayside?', a: 'Bayside is served by Ausgrid.' },
      { q: 'What solar system size suits Bayside homes?', a: 'Bayside has mainly post-war detached and semi-detached homes. A 5–10 kW system is typical. Use the checker above to see your specific roof capacity.' },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 574,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Randwick?', a: `Randwick receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years.` },
      { q: 'Are there heritage restrictions on solar in Randwick?', a: 'Randwick has 574 heritage items. Coogee, Kensington, and Randwick itself have significant heritage conservation areas. Solar on terrace houses and Federation-era homes in conservation areas requires council approval.' },
      { q: 'What solar systems suit Randwick homes?', a: 'Randwick has a mix of terrace houses, semi-detached homes, and apartment buildings. North-facing rear roofs on terraces can often fit a 3–5 kW system. Larger detached homes can accommodate 6.6–10 kW.' },
      { q: 'What network serves Randwick?', a: 'Randwick is served by Ausgrid.' },
      { q: 'Does salt air affect solar in Randwick?', a: 'Properties near Coogee and Maroubra beaches should use C5 salt-spray rated mounting hardware. Inland Randwick suburbs are generally fine with standard mounting.' },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 633,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Waverley?', a: `Waverley receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years. Bondi area terrace houses may have limited north-facing roof area.` },
      { q: 'Are there heritage restrictions on solar in Waverley?', a: 'Waverley has 633 heritage items. Bondi, Waverley, and Bronte have significant heritage conservation areas covering many Victorian-era and interwar terrace streets. Solar typically requires a heritage impact statement and council approval in these areas.' },
      { q: 'Does the coastal location affect solar in Waverley?', a: 'Properties in Bondi and Bronte within 500m of the ocean should use marine-grade mounting. Salt spray corrosion is a real risk for standard hardware in coastal Waverley.' },
      { q: 'What network serves Waverley?', a: 'Waverley is served by Ausgrid.' },
      { q: 'What solar system fits a Waverley terrace?', a: 'Terrace houses in Waverley typically have limited roof area. A 3–5 kW system is often the maximum on a standard terrace. North-facing roofs achieve significantly better yield than east or west.' },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    sunshineHoursPerYear: 2480,
    bomStation: 'Sydney Airport',
    heritageCount: 761,
    refPaybackYears: refPayback(2480),
    faqs: [
      { q: 'Is solar worth it in Woollahra?', a: `Woollahra receives around 2,480 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2480 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2480)} years.` },
      { q: 'Does Woollahra\'s heritage status affect solar installation?', a: 'Woollahra has 761 heritage items — one of Sydney\'s highest densities. Paddington, Woollahra village, and Double Bay have extensive heritage conservation areas. Solar on properties in these areas almost always requires a heritage impact assessment and council approval.' },
      { q: 'Can I install solar on a Paddington terrace?', a: 'Solar on Paddington terraces is possible but restricted. Panels must generally be on rear roof sections not visible from the street, and must not damage heritage fabric. Council approval and a heritage consultant assessment are typically required.' },
      { q: 'What network serves Woollahra?', a: 'Woollahra is served by Ausgrid.' },
      { q: 'What solar system size fits Woollahra homes?', a: 'Woollahra\'s terrace-dense suburbs limit roof area. A 3–5 kW system is typical for terraces. Larger detached homes in Bellevue Hill and Woollahra itself can accommodate 6.6–10 kW.' },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    sunshineHoursPerYear: 2490,
    bomStation: 'Sydney Airport',
    heritageCount: 477,
    refPaybackYears: refPayback(2490),
    faqs: [
      { q: 'Is solar worth it in the Sutherland Shire?', a: `The Sutherland Shire receives around 2,490 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2490 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2490)} years. The Shire\'s predominantly detached housing stock suits larger solar systems.` },
      { q: 'Are there heritage restrictions on solar in the Sutherland Shire?', a: 'Sutherland Shire has 477 heritage items. Heritage conservation areas exist in Cronulla, Gymea, and older parts of Miranda and Caringbah. Check your address if near a conservation area.' },
      { q: 'Does salt air affect solar near Cronulla and beaches?', a: 'Coastal properties near Cronulla, Bundeena, and Maianbar should use marine-grade mounting hardware. Properties more than 2 km from the coast are generally fine with standard hardware.' },
      { q: 'What network serves the Sutherland Shire?', a: 'The Sutherland Shire is served by Ausgrid.' },
      { q: 'What solar system size suits Sutherland Shire homes?', a: 'The Shire\'s larger-block suburban homes often support 10–13 kW systems. Systems with battery storage are increasingly popular in the area. Use the checker above to see your specific roof capacity.' },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    sunshineHoursPerYear: 2550,
    bomStation: 'Campbelltown',
    heritageCount: 149,
    refPaybackYears: refPayback(2550),
    faqs: [
      { q: 'Is solar worth it in Camden?', a: `Camden receives around 2,550 sunshine hours per year — above the Sydney CBD average. A 6.6 kW system yields approximately ${Math.round(2550 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2550)} years. New estates have large north-facing roofs ideal for solar.` },
      { q: 'Are there heritage restrictions on solar in Camden?', a: 'Camden has 149 heritage items, mainly in the Camden Town heritage conservation area. New estate properties are typically outside heritage areas. Check your address if in the historic Camden town precinct.' },
      { q: 'What solar systems suit Camden new estates?', a: 'New Camden developments typically have large, north-oriented roof areas on single and double-storey homes. Systems of 10–13 kW are common and economically viable given the sunshine hours and larger household electricity consumption.' },
      { q: 'What network serves Camden?', a: 'Camden is served by Endeavour Energy.' },
      { q: 'Is battery storage worth it in Camden?', a: 'Camden\'s high sunshine hours and larger homes make battery storage particularly viable. A 10 kWh battery paired with a 10+ kW system can increase self-consumption to 60–70%, significantly improving the overall return.' },
    ],
  },
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    sunshineHoursPerYear: 2580,
    bomStation: 'Campbelltown',
    heritageCount: 116,
    refPaybackYears: refPayback(2580),
    faqs: [
      { q: 'Is solar worth it in Campbelltown?', a: `Campbelltown receives around 2,580 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2580 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2580)} years — among the best in Greater Sydney.` },
      { q: 'Are there heritage restrictions on solar in Campbelltown?', a: 'Campbelltown has 116 heritage items, primarily in the Campbelltown city centre heritage conservation area. Most suburban properties are outside heritage areas.' },
      { q: 'What solar systems suit Campbelltown homes?', a: 'Campbelltown\'s predominantly detached suburban homes suit 6.6–13.2 kW systems. The combination of high sunshine hours and larger households makes solar particularly cost-effective here.' },
      { q: 'What network serves Campbelltown?', a: 'Campbelltown is served by Endeavour Energy.' },
      { q: 'Is battery storage worth it in Campbelltown?', a: 'Yes — Campbelltown\'s high sunshine hours (2,580/year) and larger homes make battery storage a strong investment alongside solar. Self-consumption rates of 60%+ are achievable with a 10 kWh battery.' },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    sunshineHoursPerYear: 2550,
    bomStation: 'Liverpool',
    heritageCount: 97,
    refPaybackYears: refPayback(2550),
    faqs: [
      { q: 'Is solar worth it in Liverpool?', a: `Liverpool receives around 2,550 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2550 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2550)} years.` },
      { q: 'Are there heritage restrictions on solar in Liverpool?', a: 'Liverpool has 97 heritage items — relatively few. Most are in the Liverpool CBD heritage precinct. Suburban residential properties are generally not heritage-affected.' },
      { q: 'What solar systems suit Liverpool homes?', a: 'Liverpool\'s predominantly detached and semi-detached suburban homes suit 6.6–13.2 kW systems. New estates in Edmondson Park and Carnes Hill can accommodate larger systems.' },
      { q: 'What network serves Liverpool?', a: 'Liverpool is served by Endeavour Energy.' },
      { q: 'What are average solar savings in Liverpool?', a: `At 2,550 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2550 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2550 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year at current NSW tariffs.` },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    sunshineHoursPerYear: 2600,
    bomStation: 'Penrith',
    heritageCount: 253,
    refPaybackYears: refPayback(2600),
    faqs: [
      { q: 'Is solar worth it in Penrith?', a: `Penrith receives around 2,600 sunshine hours per year -- the highest of any Greater Sydney LGA in our analysis. A 6.6 kW system yields approximately ${Math.round(2600 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2600)} years.` },
      { q: 'Are there heritage restrictions on solar in Penrith?', a: 'Penrith has 253 heritage items, mainly around the Penrith CBD and Emu Plains historic area. Most suburban residential properties are outside heritage areas.' },
      { q: 'What solar systems suit Penrith homes?', a: 'Penrith\'s hot summers and high sunshine hours, combined with predominantly detached suburban homes, make it ideal for large solar systems with battery storage. Systems of 10-20 kW are common and cost-effective.' },
      { q: 'What network serves Penrith?', a: 'Penrith is served by Endeavour Energy.' },
      { q: 'Is battery storage particularly worth it in Penrith?', a: 'Yes -- Penrith\'s high summer temperatures and long sunshine hours (2,600/year) make battery storage very viable. Air conditioning demand is high in summer, and a battery can shift solar generation to evening peak use.' },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    sunshineHoursPerYear: 2630,
    bomStation: 'Richmond',
    heritageCount: 604,
    refPaybackYears: refPayback(2630),
    faqs: [
      { q: 'Is solar worth it in Hawkesbury?', a: `Hawkesbury receives around 2,630 sunshine hours per year (BOM Richmond station). A 6.6 kW system yields approximately ${Math.round(2630 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2630)} years -- one of the better returns among NSW regional LGAs.` },
      { q: 'Are there heritage restrictions on solar in Hawkesbury?', a: 'Hawkesbury has 604 heritage items including significant colonial-era buildings in Windsor and Richmond. Solar on heritage-listed properties or in heritage conservation areas requires development consent from Hawkesbury City Council. The Windsor and Richmond historic precincts have particularly strict controls on visible rooftop modifications.' },
      { q: 'What network serves Hawkesbury?', a: 'Hawkesbury is served by Endeavour Energy. Feed-in tariffs are set by your electricity retailer -- compare current offers at energymadeeasy.gov.au.' },
      { q: 'Does flooding affect solar installations in Hawkesbury?', a: 'Hawkesbury is one of Australia\'s most flood-prone LGAs. Flood-affected properties should consult their installer about panel placement height and electrical component positioning to avoid flood damage risk.' },
      { q: 'What solar system size suits Hawkesbury properties?', a: 'Hawkesbury\'s rural-residential and acreage properties can accommodate large systems. Systems of 10-20 kW are common and financially strong given the high sunshine hours. Use the checker above to see your specific roof capacity.' },
    ],
  },
  {
    name: 'Wollongong',
    slug: 'wollongong',
    sunshineHoursPerYear: 2470,
    bomStation: 'Wollongong',
    heritageCount: 519,
    refPaybackYears: refPayback(2470),
    faqs: [
      { q: 'Is solar worth it in Wollongong?', a: `Wollongong receives around 2,470 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2470 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2470)} years. The Illawarra escarpment to the west can cause late-afternoon shading on some properties.` },
      { q: 'Are there heritage restrictions on solar in Wollongong?', a: 'Wollongong has 519 heritage items. Heritage conservation areas in Wollongong CBD, Bulli, and Thirroul may require council approval for solar. Check your address if near a heritage-listed building or conservation precinct.' },
      { q: 'What network serves Wollongong?', a: 'Wollongong is served by Endeavour Energy. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'Does the escarpment affect solar in Wollongong?', a: 'Properties on the western slopes of the Illawarra escarpment or in valleys may experience shading from terrain in the afternoon. The aerial imagery analysis estimates roof area but cannot model terrain shading -- an on-site assessment is recommended for escarpment-facing properties.' },
      { q: 'What solar system size suits Wollongong homes?', a: 'Wollongong\'s mix of post-war detached homes and newer estates suits 6.6-10 kW systems. Larger properties in Figtree and Keiraville can accommodate bigger systems. Use the checker above for your specific roof estimate.' },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    sunshineHoursPerYear: 2690,
    bomStation: 'Grafton',
    heritageCount: 1153,
    refPaybackYears: refPayback(2690),
    faqs: [
      { q: 'Is solar worth it in Clarence Valley?', a: `Clarence Valley receives around 2,690 sunshine hours per year (BOM Grafton station) -- well above the Sydney average. A 6.6 kW system yields approximately ${Math.round(2690 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2690)} years.` },
      { q: 'Are there heritage restrictions on solar in Clarence Valley?', a: 'Clarence Valley has 1,153 heritage items -- one of the highest counts of any NSW LGA. Grafton\'s jacaranda-lined streets and many historic homesteads are listed. Solar on heritage-listed properties requires development consent and a heritage impact assessment.' },
      { q: 'What network serves Clarence Valley?', a: 'Clarence Valley is served by Essential Energy. Feed-in tariffs are set by your electricity retailer -- compare at energymadeeasy.gov.au.' },
      { q: 'Does flood risk affect solar installations in Clarence Valley?', a: 'Parts of Clarence Valley are highly flood-prone, particularly near the Clarence River and its tributaries. Electrical components and mounting systems should be placed above flood levels where possible. Consult your installer about flood-resilient system design.' },
      { q: 'What are typical solar savings in Clarence Valley?', a: `At 2,690 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2690 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2690 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year at current NSW tariff benchmarks.` },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    sunshineHoursPerYear: 2610,
    bomStation: 'Yass',
    heritageCount: 332,
    refPaybackYears: refPayback(2610),
    faqs: [
      { q: 'Is solar worth it in Yass Valley?', a: `Yass Valley receives around 2,610 sunshine hours per year. A 6.6 kW system yields approximately ${Math.round(2610 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2610)} years. The inland tablelands climate delivers strong solar performance with minimal coastal cloud cover.` },
      { q: 'Are there heritage restrictions on solar in Yass Valley?', a: 'Yass Valley has 332 heritage items, concentrated in the Yass town centre and historic pastoral properties. Solar on listed buildings or in the Yass heritage conservation area requires council approval and a heritage impact assessment.' },
      { q: 'What network serves Yass Valley?', a: 'Yass Valley is served by Essential Energy. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'What solar system size suits Yass Valley properties?', a: 'Yass Valley\'s rural-residential and town-lot properties vary widely. Town homes typically suit 6.6-10 kW systems; larger rural properties can accommodate 13-20 kW systems. Use the checker above to estimate your specific roof capacity.' },
      { q: 'Is battery storage worth it in Yass Valley?', a: 'Yes -- Yass Valley\'s high sunshine hours and the prevalence of larger homes make battery storage a strong investment. Power outages during storms are more common than in metro areas, adding resilience value on top of the financial return.' },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    sunshineHoursPerYear: 2790,
    bomStation: 'Forbes',
    heritageCount: 168,
    refPaybackYears: refPayback(2790),
    faqs: [
      { q: 'Is solar worth it in Forbes?', a: `Forbes receives around 2,790 sunshine hours per year -- significantly above the Sydney average. A 6.6 kW system yields approximately ${Math.round(2790 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2790)} years. The central west climate is one of the most solar-favourable in NSW.` },
      { q: 'Are there heritage restrictions on solar in Forbes?', a: 'Forbes has 168 heritage items, mainly in the Forbes town centre conservation area. Most residential properties in Forbes are outside heritage areas. Check your address if near the central business district.' },
      { q: 'What network serves Forbes?', a: 'Forbes is served by Essential Energy. Feed-in tariffs are set by your electricity retailer -- compare at energymadeeasy.gov.au.' },
      { q: 'What solar system size suits Forbes homes?', a: 'Forbes\'s predominantly single-storey homes on larger lots suit 6.6-13 kW systems. The high sunshine hours make larger systems particularly cost-effective. Use the checker above to estimate your specific roof capacity.' },
      { q: 'What are typical solar savings in Forbes?', a: `At 2,790 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2790 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2790 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year -- among the highest savings of any LGA in this analysis.` },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    sunshineHoursPerYear: 2840,
    bomStation: 'Tamworth Airport',
    heritageCount: 513,
    refPaybackYears: refPayback(2840),
    faqs: [
      { q: 'Is solar worth it in Tamworth Regional?', a: `Tamworth receives around 2,840 sunshine hours per year (BOM Tamworth Airport station) -- the highest of any LGA in this analysis. A 6.6 kW system yields approximately ${Math.round(2840 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2840)} years.` },
      { q: 'Are there heritage restrictions on solar in Tamworth?', a: 'Tamworth Regional has 513 heritage items. The Tamworth city centre heritage conservation area and several residential precincts have heritage listings. Solar on listed properties or in conservation areas requires development consent from Tamworth Regional Council.' },
      { q: 'What network serves Tamworth Regional?', a: 'Tamworth Regional is served by Essential Energy. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'How does Tamworth\'s climate affect solar performance?', a: 'Tamworth\'s inland climate delivers very high solar irradiance with hot, dry summers and clear winter days. The combination of high sunshine hours and relatively low cloud cover means consistent year-round generation -- making battery storage very viable here.' },
      { q: 'What are typical solar savings in Tamworth Regional?', a: `At 2,840 sunshine hours/year, a 6.6 kW system saves approximately $${Math.round((2840 * 6.6 * 0.8 * SELF_CONSUME_RATIO * RETAIL_RATE) + (2840 * 6.6 * 0.8 * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE)).toLocaleString()}/year at current NSW tariff benchmarks.` },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    sunshineHoursPerYear: 2640,
    bomStation: 'Bathurst Agricultural',
    heritageCount: 431,
    refPaybackYears: refPayback(2640),
    faqs: [
      { q: 'Is solar worth it in Bathurst Regional?', a: `Bathurst receives around 2,640 sunshine hours per year (BOM Bathurst Agricultural station). A 6.6 kW system yields approximately ${Math.round(2640 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2640)} years. Bathurst\'s tablelands climate delivers good solar yield despite cool winters.` },
      { q: 'Are there heritage restrictions on solar in Bathurst?', a: 'Bathurst Regional has 431 heritage items. The Bathurst city centre and several residential precincts have heritage conservation areas. Solar on historic terrace houses and listed properties in the conservation area requires council approval and a heritage impact assessment.' },
      { q: 'What network serves Bathurst Regional?', a: 'Bathurst Regional is served by Essential Energy. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'Does Bathurst\'s cold winter affect solar output?', a: 'Cold winters reduce solar output slightly compared to warmer regions, but Bathurst\'s 2,640 annual sunshine hours account for this. Clear winter days still generate useful output. Panel efficiency actually improves in cold temperatures -- the net effect is modest.' },
      { q: 'What solar system size suits Bathurst homes?', a: 'Bathurst\'s mix of heritage terrace houses and suburban homes suits 5-10 kW systems. Newer estates on the city fringe can accommodate larger 10-13 kW systems. Use the checker above to estimate your specific roof capacity.' },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    sunshineHoursPerYear: 2350,
    bomStation: 'Bowral',
    heritageCount: 577,
    refPaybackYears: refPayback(2350),
    faqs: [
      { q: 'Is solar worth it in Wingecarribee (Southern Highlands)?', a: `Wingecarribee receives around 2,350 sunshine hours per year (BOM Bowral station) -- the lowest of any LGA in this analysis, reflecting the cooler, cloudier Southern Highlands climate. A 6.6 kW system yields approximately ${Math.round(2350 * 6.6 * 0.8).toLocaleString()} kWh/year with a payback of about ${refPayback(2350)} years.` },
      { q: 'Are there heritage restrictions on solar in Wingecarribee?', a: 'Wingecarribee has 577 heritage items. Bowral, Moss Vale, and Berrima have significant heritage conservation areas. Solar on heritage-listed properties or in conservation areas requires development consent from Wingecarribee Shire Council and a heritage impact assessment.' },
      { q: 'What network serves Wingecarribee?', a: 'Wingecarribee is served by Endeavour Energy. Feed-in tariffs are set by your electricity retailer.' },
      { q: 'Does cloud cover affect solar in the Southern Highlands?', a: 'The Southern Highlands is cloudier than inland NSW, which reduces the effective sunshine hours. The 2,350 sunshine hours figure accounts for local cloud patterns (BOM Bowral data). Installers should use local irradiance data rather than Sydney or Canberra figures when sizing a system here.' },
      { q: 'Is battery storage worth it in Wingecarribee?', a: 'Battery storage adds resilience value in the Southern Highlands where storms cause more frequent outages than in metro areas. The financial return is lower than in sunnier LGAs, but the combination of blackout protection and reduced grid dependence makes it worth considering for larger households.' },
    ],
  },
]

export const SOLAR_LGA_SLUG_MAP: Record<string, SolarLgaData> = Object.fromEntries(
  SOLAR_LGAS.map(lga => [lga.slug, lga])
)

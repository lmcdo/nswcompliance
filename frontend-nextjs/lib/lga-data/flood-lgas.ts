export interface FloodLgaData {
  name: string
  slug: string
  /** Total flood features in spatial_overlays */
  floodFeatureCount: number
  /** ARI scenarios if available — empty array = FPA-only */
  ariScenarios: string[]
  floodStudyName: string
  heritageCount: number
  faqs: Array<{ q: string; a: string }>
}

export const FLOOD_LGAS: FloodLgaData[] = [
  // ── Greater Sydney — Inner & East ──────────────────────────────────
  {
    name: 'Inner West',
    slug: 'inner-west',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Inner West Flood Planning',
    heritageCount: 2039,
    faqs: [
      {
        q: 'Is my Inner West property in a flood planning area?',
        a: 'Parts of the Inner West are in flood planning areas, particularly near the Cooks River, Hawthorne Canal, and creek lines through Marrickville, Leichhardt, and Ashfield. Use the checker above to see if your specific address is within the mapped flood planning area.',
      },
      {
        q: 'What are the main flood risks in the Inner West?',
        a: 'The Cooks River and its tributaries, Hawthorne Canal, and local overland flow paths are the primary flood sources. The Inner West has experienced significant flash flooding in recent years, particularly in low-lying areas near creek lines.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in the Inner West?',
        a: 'Yes. Under SEPP Housing 2021, properties on flood control lots cannot use the complying development (CDC) pathway for secondary dwellings. A DA with flood risk assessment is required instead.',
      },
      {
        q: 'How do I get the official flood status for an Inner West property?',
        a: 'A Section 10.7 Planning Certificate from Inner West Council is the authoritative source. This discloses statutory flood information and is required for conveyancing.',
      },
    ],
  },
  {
    name: 'Bayside',
    slug: 'bayside',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Bayside Flood Planning',
    heritageCount: 424,
    faqs: [
      {
        q: 'Is my Bayside property in a flood planning area?',
        a: 'Parts of Bayside near the Cooks River, Muddy Creek, and low-lying areas around Botany Bay are within flood planning areas. Use the checker above to confirm your address.',
      },
      {
        q: 'What are the flood risks in Bayside?',
        a: 'The Cooks River, tidal influences from Botany Bay, and local drainage systems are the primary flood sources. Low-lying areas in Arncliffe, Wolli Creek, and parts of Rockdale are most affected.',
      },
      {
        q: 'Does flood zone status affect development in Bayside?',
        a: 'Yes. Properties in flood planning areas face additional development controls including minimum floor levels, flood-compatible construction, and potentially flood risk assessment requirements for DAs.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Bayside property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. A DA with flood risk assessment is required for secondary dwellings on flood-affected land.',
      },
    ],
  },
  {
    name: 'Randwick',
    slug: 'randwick',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Randwick Flood Planning',
    heritageCount: 574,
    faqs: [
      {
        q: 'Is my Randwick property in a flood planning area?',
        a: 'Some parts of Randwick have flood planning areas, particularly near overland flow paths and low-lying areas near Botany Bay. Coastal areas may also be affected by tidal inundation mapping. Check your specific address above.',
      },
      {
        q: 'What flood risks exist in Randwick?',
        a: 'Overland flow from intense rainfall is the primary flood risk in Randwick, rather than riverine flooding. Low-lying areas near Maroubra, Kingsford, and parts of Randwick can experience flash flooding during heavy rain events.',
      },
      {
        q: 'Does flood risk affect insurance in Randwick?',
        a: 'Properties in mapped flood zones typically face higher insurance premiums. Check your Section 10.7 certificate for official flood status, which is the reference insurers use when pricing policies.',
      },
    ],
  },
  {
    name: 'Waverley',
    slug: 'waverley',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Waverley Flood Planning',
    heritageCount: 633,
    faqs: [
      {
        q: 'Is my Waverley property in a flood planning area?',
        a: 'Waverley has limited flood planning areas, primarily associated with overland flow paths. The hilly coastal terrain means most properties drain well, but low points in the streetscape can be affected during intense rainfall.',
      },
      {
        q: 'What flood risks exist in Waverley?',
        a: 'Overland stormwater flow is the main risk in Waverley. The steep topography can concentrate runoff in low-lying properties during intense rainfall events. Coastal erosion and wave overtopping are separate hazards managed under coastal hazard provisions.',
      },
      {
        q: 'Does flood status affect development in Waverley?',
        a: 'For the small number of properties in flood planning areas, development controls apply. Minimum floor levels and flood-compatible construction may be required. Check your address above for an indicative assessment.',
      },
    ],
  },
  {
    name: 'Woollahra',
    slug: 'woollahra',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Woollahra Flood Planning',
    heritageCount: 761,
    faqs: [
      {
        q: 'Is my Woollahra property in a flood planning area?',
        a: 'Woollahra has limited flood planning areas. Some properties near harbour foreshore areas and in low-lying parts of Double Bay and Rose Bay may be affected by tidal inundation or overland flow mapping.',
      },
      {
        q: 'What flood risks exist in Woollahra?',
        a: 'Harbour foreshore inundation and overland stormwater flow during intense rainfall are the primary risks. The hilly terrain of Woollahra generally provides good drainage, but low-lying properties near the harbour can be affected.',
      },
      {
        q: 'Does flood status affect heritage property renovations in Woollahra?',
        a: 'If your heritage property is also in a flood planning area, both heritage and flood development controls apply. This can create complex DA requirements. Check both statuses before planning any renovation work.',
      },
    ],
  },
  // ── Greater Sydney — North ─────────────────────────────────────────
  {
    name: 'Northern Beaches',
    slug: 'northern-beaches',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Northern Beaches Flood Planning',
    heritageCount: 956,
    faqs: [
      {
        q: 'Is my Northern Beaches property in a flood planning area?',
        a: 'Parts of the Northern Beaches have flood planning areas, particularly along Narrabeen Lagoon, Dee Why Lagoon, and Manly Creek. Coastal lagoon areas are most affected. Check your specific address above.',
      },
      {
        q: 'What flood risks exist on the Northern Beaches?',
        a: 'Coastal lagoon flooding (Narrabeen, Dee Why, Curl Curl), creek flooding (Manly Creek, Middle Creek), and overland flow are the main risks. The 2022 storms caused significant flooding around Narrabeen Lagoon.',
      },
      {
        q: 'Does flood risk affect development on the Northern Beaches?',
        a: 'Properties in flood planning areas face development controls including minimum floor levels and flood-compatible construction. The Northern Beaches DCP has specific provisions for flood-affected land.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Northern Beaches property?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the CDC pathway. A DA with flood risk assessment is required. Check your flood status above, then use the granny flat checker for full CDC eligibility.',
      },
    ],
  },
  {
    name: 'Ku-ring-gai',
    slug: 'ku-ring-gai',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Ku-ring-gai Flood Planning',
    heritageCount: 1046,
    faqs: [
      {
        q: 'Is my Ku-ring-gai property in a flood planning area?',
        a: 'Some Ku-ring-gai properties are in flood planning areas, particularly near creek lines and in lower-lying areas of Gordon, Pymble, and Wahroonga. The steep terrain can create flash flood risk along creek corridors.',
      },
      {
        q: 'What flood risks exist in Ku-ring-gai?',
        a: 'Creek flooding from Lane Cove River tributaries, Middle Harbour tributaries, and local overland flow are the main risks. The steep terrain means water moves quickly during heavy rain, creating flash flood risk in valley areas.',
      },
      {
        q: 'Does flood risk overlap with bushfire in Ku-ring-gai?',
        a: 'In some areas, yes. Creek corridors can be both flood-affected and bordered by bushfire-prone vegetation. Properties with dual constraints face additional development assessment requirements.',
      },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Hornsby Flood Planning',
    heritageCount: 769,
    faqs: [
      {
        q: 'Is my Hornsby property in a flood planning area?',
        a: 'Hornsby Shire Council has flood planning areas defined under the Hornsby LEP. Berowra Creek, Cowan Creek, and their tributaries are the main flood risk areas on the northern edge of the shire. Suburban areas closer to the train lines generally have lower flood risk.',
      },
      {
        q: 'Which Hornsby suburbs have flood risk?',
        a: 'Flood risk in Hornsby Shire is most pronounced near Berowra Waters, Cowan, and low-lying areas along creek lines through suburbs like Hornsby, Waitara, and Asquith. Use the checker above to confirm whether your specific address is within the mapped flood planning area.',
      },
      {
        q: 'Does flood zone status affect development approvals in Hornsby?',
        a: 'Yes. Properties in Hornsby\'s flood planning areas face additional development controls. Minimum floor levels above the flood planning level, flood-compatible materials, and formal flood risk assessment may all be required depending on the type of development proposed.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Hornsby property?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the complying development pathway. If your Hornsby property is in the flood planning area, a secondary dwelling requires a DA. Check your full SEPP eligibility using the granny flat checker after confirming flood status above.',
      },
    ],
  },
  {
    name: 'Lane Cove',
    slug: 'lane-cove',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Lane Cove Flood Planning',
    heritageCount: 287,
    faqs: [
      {
        q: 'Is my Lane Cove property in a flood planning area?',
        a: 'Some Lane Cove properties near the Lane Cove River and its tributaries are in flood planning areas. Low-lying areas near the river and in the Lane Cove town centre precinct may be affected.',
      },
      {
        q: 'What flood risks exist in Lane Cove?',
        a: 'The Lane Cove River and local creek tributaries are the main flood sources. The river valley creates a natural floodplain that affects some properties along the watercourse.',
      },
      {
        q: 'Does flood status affect development in Lane Cove?',
        a: 'Properties in flood planning areas face additional controls including minimum floor levels and flood risk assessment requirements. Lane Cove Council\'s DCP has provisions for development on flood-affected land.',
      },
    ],
  },
  {
    name: 'Ryde',
    slug: 'ryde',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Ryde Flood Planning',
    heritageCount: 412,
    faqs: [
      {
        q: 'Is my Ryde property in a flood planning area?',
        a: 'Parts of Ryde near the Parramatta River, Lane Cove River, and their tributaries have flood planning areas. Low-lying areas in Meadowbank, Ryde, and Marsfield may be affected.',
      },
      {
        q: 'What flood risks exist in Ryde?',
        a: 'The Parramatta River and Lane Cove River create the primary flood risk. Shrimptons Creek through Marsfield and other local waterways also have flood planning areas defined under the Ryde LEP.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Ryde?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. Check your flood status above, then use the granny flat checker for full CDC eligibility assessment.',
      },
    ],
  },
  // ── Greater Sydney — West ──────────────────────────────────────────
  {
    name: 'Parramatta',
    slug: 'parramatta',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Parramatta Flood Planning',
    heritageCount: 803,
    faqs: [
      {
        q: 'Is my Parramatta property in a flood planning area?',
        a: 'Significant parts of Parramatta are in flood planning areas, particularly along the Parramatta River, Clay Cliff Creek, and Toongabbie Creek. The Parramatta CBD itself has flood-affected areas. Check your specific address above.',
      },
      {
        q: 'What are the main flood risks in Parramatta?',
        a: 'The Parramatta River catchment creates the primary flood risk. The river has significant flood history, with major events in 2021 and 2022. Overland flow during intense rainfall also affects parts of the LGA away from watercourses.',
      },
      {
        q: 'Does the Parramatta River flood study affect development?',
        a: 'Yes. Properties in the Parramatta River flood planning area face development controls including minimum floor levels, flood-compatible construction, and formal flood risk assessment for certain development types.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Parramatta property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. A DA with flood risk assessment is required for secondary dwellings on flood-affected land in Parramatta.',
      },
    ],
  },
  {
    name: 'Blacktown',
    slug: 'blacktown',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Blacktown Flood Planning',
    heritageCount: 131,
    faqs: [
      {
        q: 'Is my Blacktown property in a flood planning area?',
        a: 'Parts of Blacktown have flood planning areas, particularly along Eastern Creek, Bells Creek, and Ropes Creek. New release areas in the north-west may also have flood-affected land near natural watercourses.',
      },
      {
        q: 'What flood risks exist in Blacktown?',
        a: 'Eastern Creek, Bells Creek, and their tributaries are the main flood sources. Overland flow in low-lying areas of established suburbs also creates flood risk during intense rainfall events.',
      },
      {
        q: 'Does flood risk affect new housing estates in Blacktown?',
        a: 'New release areas must address flood risk at the subdivision stage. Some lots near natural watercourses may be in flood planning areas. Check your specific lot before purchase.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Blacktown property?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the CDC pathway. Check your flood status above, then use the granny flat checker for full eligibility assessment.',
      },
    ],
  },
  {
    name: 'The Hills Shire',
    slug: 'the-hills-shire',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'The Hills Flood Planning',
    heritageCount: 223,
    faqs: [
      {
        q: 'Is my Hills Shire property in a flood planning area?',
        a: 'Parts of The Hills Shire have flood planning areas, particularly along Cattai Creek, Caddies Creek, and tributaries of the Hawkesbury River in the northern portion of the LGA.',
      },
      {
        q: 'What flood risks exist in The Hills Shire?',
        a: 'Creek flooding from Cattai Creek and its tributaries is the primary risk. Low-lying rural-residential areas in the north of the LGA near the Hawkesbury River are also affected. Urban areas around Castle Hill generally have lower flood risk.',
      },
      {
        q: 'Does flood risk affect development in new release areas of The Hills?',
        a: 'New release areas including Box Hill must address flood risk in subdivision design. Some lots near creek corridors may be in flood planning areas with development controls.',
      },
    ],
  },
  {
    name: 'Penrith',
    slug: 'penrith',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Penrith Flood Planning',
    heritageCount: 253,
    faqs: [
      {
        q: 'Is my Penrith property in a flood planning area?',
        a: 'Significant parts of Penrith are in flood planning areas. The Nepean River, South Creek, and their tributaries create extensive flood-affected areas. Properties in Emu Plains, Penrith CBD, and low-lying western suburbs should check their status.',
      },
      {
        q: 'What are the main flood risks in Penrith?',
        a: 'The Hawkesbury-Nepean River system and South Creek are the primary flood sources. Penrith is part of the Hawkesbury-Nepean catchment, which has one of the largest flood risk exposures in Australia. Major flood events occurred in 2021 and 2022.',
      },
      {
        q: 'Does flood risk overlap with bushfire in Penrith?',
        a: 'Yes. Properties along the Nepean River corridor may face both flood and bushfire constraints — flood from the river and bushfire from adjacent Blue Mountains vegetation. Dual constraints increase development assessment complexity.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Penrith property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. Given the extent of flood-affected land in Penrith, checking flood status before planning a granny flat is essential.',
      },
    ],
  },
  {
    name: 'Hawkesbury',
    slug: 'hawkesbury',
    floodFeatureCount: 1256,
    ariScenarios: ['1-in-2yr', '1-in-5yr', '1-in-10yr', '1-in-20yr', '1-in-50yr', '1-in-100yr', '1-in-200yr', '1-in-500yr', '1-in-1000yr', '1-in-2000yr', '1-in-5000yr', 'PMF'],
    floodStudyName: 'Hawkesbury-Nepean River Flood Study 2024',
    heritageCount: 604,
    faqs: [
      {
        q: 'What flood data exists for Hawkesbury?',
        a: 'The 2024 Hawkesbury-Nepean River Flood Study provides ARI-quantified data including 1-in-100-year through PMF scenarios. This is the most recent flood study for the Hawkesbury-Nepean catchment, published following the 2022 flood events.',
      },
      {
        q: 'How bad were the 2022 Hawkesbury floods?',
        a: 'The March 2022 flood event on the Hawkesbury-Nepean reached levels not seen since 1961 in some areas. The event triggered the 2024 flood study update. Properties in affected areas should check their statutory flood overlay classification, as some may have been reclassified following the study.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected lot in Hawkesbury?',
        a: 'Under SEPP Housing 2021, properties on flood control lots are ineligible for complying development (CDC) for secondary dwellings. A DA with a flood risk management report is required. The Hawkesbury-Nepean catchment has significant flood-mapped areas — use the checker above to see your address\'s flood status.',
      },
      {
        q: 'Does flood status affect property values in Hawkesbury?',
        a: 'Flood zone classification is a material fact in NSW property transactions and must be disclosed in a Section 10.7 certificate. Properties in high flood risk zones typically face lower market values, higher insurance premiums, and potential restrictions on future development.',
      },
    ],
  },
  // ── Greater Sydney — South & Southwest ─────────────────────────────
  {
    name: 'Campbelltown',
    slug: 'campbelltown',
    floodFeatureCount: 26051,
    ariScenarios: ['0.2% AEP', '0.5% AEP', '1% AEP', '2% AEP', '5% AEP', '20% AEP', 'PMF'],
    floodStudyName: 'Campbelltown Flood Study',
    heritageCount: 116,
    faqs: [
      {
        q: 'What flood zones exist in Campbelltown?',
        a: 'Campbelltown has ARI-quantified flood data covering 0.2% AEP (1-in-500-year) through PMF (Probable Maximum Flood). The 1% AEP (1-in-100-year) zone is the primary planning standard under the Campbelltown LEP. Properties in the 1% AEP zone are in the Flood Planning Area and face development controls.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Campbelltown?',
        a: 'Yes. Under SEPP Housing 2021, a property on a flood control lot is ineligible for complying development (CDC). If your Campbelltown address is in the 1% AEP flood zone, a granny flat requires a DA with a flood risk management report.',
      },
      {
        q: 'What is a Flood Planning Area in NSW?',
        a: 'A Flood Planning Area (FPA) is a zone defined in a council\'s LEP where development controls apply due to flood risk. Being in an FPA does not automatically prohibit development — it triggers additional assessment requirements, including a flood risk management report for certain development types.',
      },
      {
        q: 'Does flood risk affect property insurance in Campbelltown?',
        a: 'Yes. Properties in Campbelltown\'s flood planning areas typically face higher building and contents insurance premiums. Some insurers apply flood exclusions for high-risk AEP zones.',
      },
    ],
  },
  {
    name: 'Camden',
    slug: 'camden',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Camden Flood Planning',
    heritageCount: 149,
    faqs: [
      {
        q: 'Is my Camden property in a flood planning area?',
        a: 'Parts of Camden have flood planning areas, particularly along the Nepean River and its tributaries. Some new release areas near natural watercourses may also be affected. Check your specific address above.',
      },
      {
        q: 'What flood risks exist in Camden?',
        a: 'The Nepean River and South Creek are the primary flood sources. Camden is part of the Hawkesbury-Nepean catchment. Low-lying areas near the river, particularly around Camden township, have significant flood risk.',
      },
      {
        q: 'Does flood risk affect new estates in Camden?',
        a: 'New release areas must address flood risk at the subdivision stage. Some lots near the Nepean River and tributary creeks may be in flood planning areas. Always check flood status before purchasing in a new estate.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Camden property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. A DA with flood risk assessment is required for secondary dwellings on flood-affected land.',
      },
    ],
  },
  {
    name: 'Liverpool',
    slug: 'liverpool',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Liverpool Flood Planning',
    heritageCount: 97,
    faqs: [
      {
        q: 'Is my Liverpool property in a flood planning area?',
        a: 'Parts of Liverpool have significant flood planning areas, particularly along the Georges River and its tributaries. Properties in Chipping Norton, Moorebank, and parts of Liverpool CBD should check their status.',
      },
      {
        q: 'What flood risks exist in Liverpool?',
        a: 'The Georges River and its tributaries (including Cabramatta Creek and Brickmakers Creek) are the primary flood sources. Liverpool has experienced significant flooding events, and the Georges River flood study covers extensive areas.',
      },
      {
        q: 'Does flood risk affect development in Liverpool?',
        a: 'Properties in flood planning areas face development controls including minimum floor levels, flood-compatible construction, and flood risk assessment requirements for DAs.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Liverpool property?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the CDC pathway. Check your flood status above before planning any secondary dwelling.',
      },
    ],
  },
  {
    name: 'Sutherland Shire',
    slug: 'sutherland-shire',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Sutherland Shire Flood Planning',
    heritageCount: 477,
    faqs: [
      {
        q: 'Is my Sutherland Shire property in a flood planning area?',
        a: 'Some parts of Sutherland Shire have flood planning areas, particularly along the Woronora River, Hacking River, and local creek systems. Coastal areas may also be affected by tidal inundation mapping.',
      },
      {
        q: 'What flood risks exist in Sutherland Shire?',
        a: 'The Woronora River, Hacking River, and Georges River tributaries are the main flood sources. Flash flooding in creek corridors during intense rainfall is also a risk in some suburbs.',
      },
      {
        q: 'Does flood risk overlap with bushfire in Sutherland?',
        a: 'In some areas, yes. Creek corridors near Royal and Heathcote National Parks can be both flood-affected and bushfire-prone. Properties with dual constraints face additional assessment requirements.',
      },
    ],
  },
  {
    name: 'Georges River',
    slug: 'georges-river',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Georges River Flood Planning',
    heritageCount: 328,
    faqs: [
      {
        q: 'Is my Georges River property in a flood planning area?',
        a: 'Parts of Georges River LGA near the Georges River and its tributaries have flood planning areas. Properties in Oatley, Lugarno, and along the river corridor should check their status.',
      },
      {
        q: 'What flood risks exist in Georges River LGA?',
        a: 'The Georges River and Salt Pan Creek are the primary flood sources. Low-lying areas along the river, particularly near Oatley Park and Lugarno, may be in flood planning areas.',
      },
      {
        q: 'Does flood status affect development in Georges River?',
        a: 'Properties in flood planning areas face additional controls. Flood risk assessment and minimum floor levels may be required for development applications.',
      },
    ],
  },
  {
    name: 'Canterbury-Bankstown',
    slug: 'canterbury-bankstown',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Canterbury-Bankstown Flood Planning',
    heritageCount: 274,
    faqs: [
      {
        q: 'Is my Canterbury-Bankstown property in a flood planning area?',
        a: 'Parts of Canterbury-Bankstown have flood planning areas, particularly along the Cooks River, Georges River, and Salt Pan Creek. Properties in Canterbury, Campsie, and East Hills should check their status.',
      },
      {
        q: 'What flood risks exist in Canterbury-Bankstown?',
        a: 'The Cooks River, Georges River, Duck River, and Salt Pan Creek are the main flood sources. Flash flooding from overland flow during intense rainfall also affects some areas.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Canterbury-Bankstown?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the CDC pathway. Check your flood status above, then use the granny flat checker for full CDC eligibility assessment.',
      },
    ],
  },
  // ── Greater Sydney — Blue Mountains & surrounds ────────────────────
  {
    name: 'Blue Mountains',
    slug: 'blue-mountains',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Blue Mountains Flood Planning',
    heritageCount: 489,
    faqs: [
      {
        q: 'Is my Blue Mountains property in a flood planning area?',
        a: 'Some Blue Mountains properties are in flood planning areas, particularly along creek lines and in valley areas. The Grose River, Kedumba River, and local creek systems have mapped flood areas.',
      },
      {
        q: 'What flood risks exist in the Blue Mountains?',
        a: 'Creek and river flooding in valley areas is the primary risk. The steep terrain means water moves quickly during heavy rain. Flash flooding in creek corridors is more common than broad inundation.',
      },
      {
        q: 'Does flood risk overlap with bushfire in the Blue Mountains?',
        a: 'Yes. Many creek corridors in the Blue Mountains are both flood-affected and bordered by dense bushfire-prone vegetation. Properties with dual natural hazard constraints face complex development assessment requirements.',
      },
    ],
  },
  // ── Regional NSW ───────────────────────────────────────────────────
  {
    name: 'Wollongong',
    slug: 'wollongong',
    floodFeatureCount: 30,
    ariScenarios: [],
    floodStudyName: 'Wollongong Flood Planning',
    heritageCount: 519,
    faqs: [
      {
        q: 'Is my Wollongong property in a flood planning area?',
        a: 'Wollongong City Council has designated Flood Planning Areas under the Wollongong LEP. Properties within the FPA boundary are subject to flood-related development controls. Use the checker above to see if your specific address falls within the mapped flood planning area.',
      },
      {
        q: 'Does being in a flood planning area affect development in Wollongong?',
        a: 'Yes. Properties in the Wollongong flood planning area may face restrictions on certain development types, including secondary dwellings and low-lying structures. A flood risk assessment is typically required for DAs in flood-affected areas.',
      },
      {
        q: 'Can I build a granny flat if my Wollongong property is in a flood zone?',
        a: 'Under SEPP Housing 2021, a property designated as a flood control lot is ineligible for complying development (CDC). A DA with a flood risk management report would be required.',
      },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    floodFeatureCount: 9,
    ariScenarios: [],
    floodStudyName: 'Wingecarribee Flood Planning',
    heritageCount: 577,
    faqs: [
      {
        q: 'Is my Southern Highlands property in a flood planning area?',
        a: 'Wingecarribee Shire Council has mapped flood planning areas for the Southern Highlands under the Wingecarribee LEP. The Wingecarribee River and local creeks are the primary flood sources.',
      },
      {
        q: 'Which areas of the Southern Highlands have flood risk?',
        a: 'Flood risk in Wingecarribee is concentrated around the Wingecarribee River near Moss Vale and Bowral, Medway Road floodplains, and low-lying areas near local creek systems.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Wingecarribee?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway. A secondary dwelling on a flood-affected Wingecarribee property would require a DA with a flood risk management report.',
      },
    ],
  },
  {
    name: 'Shoalhaven',
    slug: 'shoalhaven',
    floodFeatureCount: 0,
    ariScenarios: [],
    floodStudyName: 'Shoalhaven Flood Planning',
    heritageCount: 387,
    faqs: [
      {
        q: 'Is my Shoalhaven property in a flood planning area?',
        a: 'Significant parts of Shoalhaven have flood planning areas, particularly along the Shoalhaven River, Crookhaven River, and in the Nowra area. Coastal villages may also be affected by tidal and storm surge mapping.',
      },
      {
        q: 'What flood risks exist in Shoalhaven?',
        a: 'The Shoalhaven River and its tributaries are the primary flood source. Nowra and surrounding areas have significant flood history. Coastal areas face combined riverine and tidal flood risks.',
      },
      {
        q: 'Does flood overlap with bushfire in Shoalhaven?',
        a: 'Yes. Shoalhaven has both extensive flood planning areas and high bushfire coverage (85% BFPL). Some properties face dual natural hazard constraints. The 2019-20 fires followed by 2022 flooding demonstrated both risks in rapid succession.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Shoalhaven property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the CDC pathway. Given the extent of Shoalhaven\'s flood planning areas, check your status before planning any secondary dwelling.',
      },
    ],
  },
  {
    name: 'Clarence Valley',
    slug: 'clarence-valley',
    floodFeatureCount: 6,
    ariScenarios: ['PMF'],
    floodStudyName: 'Clarence Valley Flood Study',
    heritageCount: 1153,
    faqs: [
      {
        q: 'Is my Clarence Valley property in a flood area?',
        a: 'The Clarence River is one of the largest catchments in NSW and creates significant flood risk across the Clarence Valley. The Clarence Valley LEP defines flood planning areas for Grafton, Maclean, Yamba, and surrounding townships.',
      },
      {
        q: 'What are the flood risks in Grafton and Maclean?',
        a: 'Grafton sits on the Clarence River floodplain and has a long history of major flood events. Maclean and the lower Clarence have additional flood risk from tidal and storm surge interaction. The 2022 floods were among the most damaging recorded.',
      },
      {
        q: 'Does flood zone status affect granny flat eligibility in Clarence Valley?',
        a: 'Yes. Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway for secondary dwellings. Much of the lower Clarence Valley is in flood planning areas.',
      },
    ],
  },
  {
    name: 'Yass Valley',
    slug: 'yass-valley',
    floodFeatureCount: 2,
    ariScenarios: ['PMF'],
    floodStudyName: 'Yass Valley Flood Study',
    heritageCount: 332,
    faqs: [
      {
        q: 'Is my Yass Valley property in a flood planning area?',
        a: 'Yass Valley Council has defined flood planning areas for the Yass River and tributary areas under the Yass Valley LEP.',
      },
      {
        q: 'What are the flood risks in Yass?',
        a: 'The Yass River through Yass township is the primary flood risk source. Low-lying areas near the river in central Yass are most susceptible to inundation.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Yass Valley property?',
        a: 'Under SEPP Housing 2021, properties on flood control lots are excluded from the complying development (CDC) pathway. A secondary dwelling requires a DA with flood assessment.',
      },
    ],
  },
  {
    name: 'Forbes',
    slug: 'forbes',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Forbes Flood Planning',
    heritageCount: 168,
    faqs: [
      {
        q: 'Is my Forbes property in a flood area?',
        a: 'Forbes sits on the Lachlan River floodplain and is one of the most flood-prone towns in central western NSW. The Forbes LEP defines flood planning areas covering significant portions of the town.',
      },
      {
        q: 'What is Forbes\'s flood history?',
        a: 'Forbes has experienced major flooding from the Lachlan River multiple times, including in 2016 and the catastrophic 2022 event which inundated large parts of the town.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Forbes?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the complying development pathway. Given the extent of Forbes\'s flood planning areas, many properties would require a DA for a secondary dwelling.',
      },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    floodFeatureCount: 19,
    ariScenarios: [],
    floodStudyName: 'Tamworth Regional Flood Planning',
    heritageCount: 513,
    faqs: [
      {
        q: 'Is my Tamworth property in a flood planning area?',
        a: 'Tamworth Regional Council has flood planning areas defined under the Tamworth Regional LEP. The Peel River and its tributaries are the primary flood risk sources.',
      },
      {
        q: 'What are the main flood risks in Tamworth?',
        a: 'The Peel River, Cockburn River, and Dungowan Creek catchments pose the primary flood risks. The flat terrain around Tamworth city makes low-lying areas susceptible to inundation during major rainfall events.',
      },
      {
        q: 'Does flood risk affect granny flat approvals in Tamworth?',
        a: 'Yes. Under SEPP Housing 2021, flood control lots are excluded from complying development pathways. If your property is in the flood planning area, a DA is required rather than a CDC.',
      },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    floodFeatureCount: 10,
    ariScenarios: [],
    floodStudyName: 'Bathurst Regional Flood Planning',
    heritageCount: 431,
    faqs: [
      {
        q: 'Is my Bathurst property in a flood planning area?',
        a: 'Bathurst Regional Council has defined flood planning areas under the Bathurst Regional LEP. The Macquarie River, Winburndale Rivulet, and local creeks are the primary flood sources.',
      },
      {
        q: 'What flood risks does Bathurst face?',
        a: 'The Macquarie River is the main flood risk for Bathurst. Lower-lying areas near the river and local drainage lines are most susceptible to inundation.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Bathurst property?',
        a: 'Under SEPP Housing 2021, properties on flood control lots cannot use the complying development (CDC) pathway. A secondary dwelling requires a DA with flood risk assessment.',
      },
    ],
  },
  // ── Non-canonical extras (existing data) ───────────────────────────
  {
    name: 'Mid-Western Regional',
    slug: 'mid-western-regional',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Mid-Western Regional Flood Planning',
    heritageCount: 501,
    faqs: [
      {
        q: 'Is my Mid-Western Regional property in a flood planning area?',
        a: 'Mid-Western Regional Council covers Mudgee, Gulgong, and surrounding areas. The Cudgegong River and tributaries are the primary flood sources around Mudgee.',
      },
      {
        q: 'What are the flood risks around Mudgee?',
        a: 'Mudgee\'s flood risk is primarily associated with the Cudgegong River. Low-lying areas near the river in central Mudgee and Gulgong are most susceptible.',
      },
      {
        q: 'Does flood risk affect granny flat approvals near Mudgee?',
        a: 'Yes. Under SEPP Housing 2021, properties on flood control lots cannot use the complying development pathway for secondary dwellings.',
      },
    ],
  },
  {
    name: 'Wentworth',
    slug: 'wentworth',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Wentworth Flood Planning',
    heritageCount: 130,
    faqs: [
      {
        q: 'Is my Wentworth property in a flood planning area?',
        a: 'Wentworth Shire sits at the junction of the Murray and Darling rivers — one of the highest flood-risk locations in regional NSW. Large portions of Wentworth town and Dareton are within mapped flood planning areas.',
      },
      {
        q: 'What are the flood risks in Wentworth?',
        a: 'The Murray-Darling junction creates significant flood risk for Wentworth and surrounds. The 2022 Murray River floods were among the most significant in decades, with record levels recorded at Wentworth gauge.',
      },
      {
        q: 'Can I build a granny flat on a Wentworth flood-affected property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway. Given the extent of Wentworth\'s flood planning areas, many properties require a DA with comprehensive flood risk assessment.',
      },
    ],
  },
]

export const FLOOD_LGA_SLUG_MAP: Record<string, FloodLgaData> = Object.fromEntries(
  FLOOD_LGAS.map(lga => [lga.slug, lga])
)

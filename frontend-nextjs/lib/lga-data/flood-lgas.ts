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
        a: 'Yes. Under SEPP Housing 2021, a property on a flood control lot is ineligible for complying development (CDC). If your Campbelltown address is in the 1% AEP flood zone, a granny flat requires a DA with a flood risk management report. Check your address above, then use the granny flat checker for the full CDC eligibility check.',
      },
      {
        q: 'What is a Flood Planning Area in NSW?',
        a: 'A Flood Planning Area (FPA) is a zone defined in a council\'s LEP where development controls apply due to flood risk. Being in an FPA does not automatically prohibit development — it triggers additional assessment requirements, including a flood risk management report for certain development types.',
      },
      {
        q: 'Does flood risk affect property insurance in Campbelltown?',
        a: 'Yes. Properties in Campbelltown\'s flood planning areas typically face higher building and contents insurance premiums. Some insurers apply flood exclusions for high-risk AEP zones. The NSW Government\'s Insurance Reference Service provides a standardised flood risk score used by most insurers.',
      },
      {
        q: 'Where does this Campbelltown flood data come from?',
        a: 'The flood data is sourced from the Campbelltown Flood Study, ingested into our PostGIS spatial database. ARI scenarios cover 0.2% through PMF. The checker also cross-references NSW EPI statutory overlays, Copernicus EMS observed events, and BOM gauge data.',
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
      {
        q: 'Where does this Hawkesbury flood data come from?',
        a: 'Data is sourced from the 2024 Hawkesbury-Nepean River Flood Study, ingested into our PostGIS spatial database. The checker also cross-references NSW EPI statutory overlays, Copernicus EMS satellite observations, and BOM Warragamba Dam gauge data.',
      },
    ],
  },
  {
    name: 'Wollongong',
    slug: 'wollongong',
    floodFeatureCount: 30,
    ariScenarios: [],
    floodStudyName: 'Wollongong Flood Planning',
    heritageCount: 0,
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
        q: 'How do I get the official flood status for my Wollongong property?',
        a: 'The definitive source is a Section 10.7 Planning Certificate from Wollongong City Council. This certificate discloses statutory flood information and is required for property conveyancing in NSW. The tool above provides an indicative check only.',
      },
      {
        q: 'Does flood zone status affect home insurance in Wollongong?',
        a: 'Yes. Properties in mapped flood zones typically attract higher insurance premiums. The ICA Flood Mapping tool and the NSW Government\'s Spatial Viewer both show flood risk data used by insurers when pricing policies.',
      },
      {
        q: 'Can I build a granny flat if my Wollongong property is in a flood zone?',
        a: 'Under SEPP Housing 2021, a property designated as a flood control lot is ineligible for complying development (CDC). A DA with a flood risk management report would be required. Check your CDC eligibility with the granny flat checker after confirming your flood status above.',
      },
    ],
  },
  {
    name: 'Tamworth Regional',
    slug: 'tamworth-regional',
    floodFeatureCount: 19,
    ariScenarios: [],
    floodStudyName: 'Tamworth Regional Flood Planning',
    heritageCount: 0,
    faqs: [
      {
        q: 'Is my Tamworth property in a flood planning area?',
        a: 'Tamworth Regional Council has flood planning areas defined under the Tamworth Regional LEP. The Peel River and its tributaries are the primary flood risk sources in the region. Use the checker above to see whether your specific address falls within the statutory flood planning area.',
      },
      {
        q: 'What are the main flood risks in Tamworth?',
        a: 'The Peel River, Cockburn River, and Dungowan Creek catchments pose the primary flood risks in the Tamworth region. The flat terrain around Tamworth city makes low-lying areas susceptible to inundation during major rainfall events.',
      },
      {
        q: 'How do flood controls affect building in Tamworth?',
        a: 'Properties in the flood planning area in Tamworth may require flood-compatible materials, minimum floor levels above the flood planning level, and in some cases a formal flood risk assessment before development approval.',
      },
      {
        q: 'Where can I get the official flood certificate for a Tamworth property?',
        a: 'A Section 10.7 Planning Certificate from Tamworth Regional Council discloses statutory flood information. This is required for conveyancing and provides the official flood zone status for any property.',
      },
      {
        q: 'Does flood risk affect granny flat approvals in Tamworth?',
        a: 'Yes. Under SEPP Housing 2021, flood control lots are excluded from complying development pathways. If your property is in the Tamworth flood planning area, a granny flat or secondary dwelling would require a DA rather than a CDC.',
      },
    ],
  },
  {
    name: 'Bathurst Regional',
    slug: 'bathurst-regional',
    floodFeatureCount: 10,
    ariScenarios: [],
    floodStudyName: 'Bathurst Regional Flood Planning',
    heritageCount: 0,
    faqs: [
      {
        q: 'Is my Bathurst property in a flood planning area?',
        a: 'Bathurst Regional Council has defined flood planning areas under the Bathurst Regional LEP. The Macquarie River, Winburndale Rivulet, and local creeks are the primary flood sources. Use the checker to see whether your address falls within the statutory flood planning area.',
      },
      {
        q: 'What flood risks does Bathurst face?',
        a: 'The Macquarie River is the main flood risk for Bathurst. Lower-lying areas near the river and local drainage lines are most susceptible to inundation. Bathurst\'s elevation (680m above sea level) generally reduces flood frequency compared to lower-lying NSW towns.',
      },
      {
        q: 'Does flood zone status affect development in Bathurst?',
        a: 'Properties within Bathurst\'s flood planning area require compliance with flood-related development controls. These may include minimum habitable floor levels, flood-compatible construction materials, and formal flood risk assessment for certain development types.',
      },
      {
        q: 'How do I get the official flood certificate for a Bathurst property?',
        a: 'A Section 10.7 Planning Certificate from Bathurst Regional Council is the authoritative source for flood status. This certificate is required for property conveyancing and discloses all planning constraints including flood risk.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Bathurst property?',
        a: 'Under SEPP Housing 2021, properties on flood control lots cannot use the complying development (CDC) pathway. If your Bathurst property is in the flood planning area, a secondary dwelling requires a DA with flood risk assessment.',
      },
    ],
  },
  {
    name: 'Wingecarribee',
    slug: 'wingecarribee',
    floodFeatureCount: 9,
    ariScenarios: [],
    floodStudyName: 'Wingecarribee Flood Planning',
    heritageCount: 0,
    faqs: [
      {
        q: 'Is my Southern Highlands property in a flood planning area?',
        a: 'Wingecarribee Shire Council has mapped flood planning areas for the Southern Highlands under the Wingecarribee LEP. The Wingecarribee River and local creeks are the primary flood sources. Use the checker above to see your address\'s flood status.',
      },
      {
        q: 'Which areas of the Southern Highlands have flood risk?',
        a: 'Flood risk in Wingecarribee is concentrated around the Wingecarribee River near Moss Vale and Bowral, Medway Road floodplains, and low-lying areas near local creek systems. Higher areas of the Southern Highlands are generally outside flood planning areas.',
      },
      {
        q: 'Does flood zone classification affect property sales in Wingecarribee?',
        a: 'Yes. Flood zone classification is disclosed on a Section 10.7 Planning Certificate, which is required in NSW conveyancing. Properties in flood planning areas must disclose this status to buyers, which can affect valuations and insurance costs.',
      },
      {
        q: 'How do I confirm flood status for a Southern Highlands property?',
        a: 'The authoritative source is a Section 10.7 Planning Certificate from Wingecarribee Shire Council. The NSW Planning Portal Spatial Viewer also shows flood planning area boundaries — search your address and enable the flood overlay layer.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Wingecarribee?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway. A secondary dwelling on a flood-affected Wingecarribee property would require a DA rather than a CDC, with a flood risk management report.',
      },
    ],
  },
  {
    name: 'Hornsby',
    slug: 'hornsby',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Hornsby Flood Planning',
    heritageCount: 0,
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
        q: 'How do I get the official flood status for a Hornsby property?',
        a: 'A Section 10.7 Planning Certificate from Hornsby Shire Council is the authoritative source. This is required for conveyancing and discloses all statutory planning constraints including flood risk. The NSW Planning Portal also shows flood planning area boundaries.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Hornsby property?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the complying development pathway. If your Hornsby property is in the flood planning area, a secondary dwelling requires a DA. Check your full SEPP eligibility using the granny flat checker after confirming flood status above.',
      },
    ],
  },
  {
    name: 'Mid-Western Regional',
    slug: 'mid-western-regional',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Mid-Western Regional Flood Planning',
    heritageCount: 0,
    faqs: [
      {
        q: 'Is my Mid-Western Regional property in a flood planning area?',
        a: 'Mid-Western Regional Council covers Mudgee, Gulgong, and surrounding areas. The Cudgegong River and tributaries are the primary flood sources around Mudgee. Use the checker above to see whether your specific address is within the mapped flood planning area.',
      },
      {
        q: 'What are the flood risks around Mudgee?',
        a: 'Mudgee\'s flood risk is primarily associated with the Cudgegong River. Low-lying areas near the river in central Mudgee and Gulgong are most susceptible. The broader Mid-Western region has experienced significant flooding events, most recently in 2022.',
      },
      {
        q: 'How does flood planning area status affect development?',
        a: 'Properties in the Mid-Western Regional flood planning area may require flood impact assessment for development applications. Development controls can include minimum floor levels, flood-compatible construction, and restrictions on flood-sensitive land uses.',
      },
      {
        q: 'Where can I get the official flood status for a Mudgee property?',
        a: 'A Section 10.7 Planning Certificate from Mid-Western Regional Council is the authoritative source. This discloses all statutory constraints including flood planning area status. The NSW Planning Portal Spatial Viewer also provides indicative flood planning area boundaries.',
      },
      {
        q: 'Does flood risk affect granny flat approvals near Mudgee?',
        a: 'Yes. Under SEPP Housing 2021, properties on flood control lots cannot use the complying development pathway for secondary dwellings. If your property is in the flood planning area, a DA is required rather than a CDC.',
      },
    ],
  },
  {
    name: 'Wentworth',
    slug: 'wentworth',
    floodFeatureCount: 2,
    ariScenarios: [],
    floodStudyName: 'Wentworth Flood Planning',
    heritageCount: 0,
    faqs: [
      {
        q: 'Is my Wentworth property in a flood planning area?',
        a: 'Wentworth Shire sits at the junction of the Murray and Darling rivers — one of the highest flood-risk locations in regional NSW. Large portions of Wentworth town and Dareton are within mapped flood planning areas. Use the checker above to confirm your address\'s status.',
      },
      {
        q: 'What are the flood risks in Wentworth?',
        a: 'The Murray-Darling junction creates significant flood risk for Wentworth and surrounds. Major flood events have inundated large areas of the town. The 2022 Murray River floods were among the most significant in decades, with record levels recorded at Wentworth gauge.',
      },
      {
        q: 'How does flood zone status affect building approvals in Wentworth?',
        a: 'Properties in Wentworth\'s flood planning area face significant development controls. Minimum floor levels well above ground level, flood-compatible construction methods, and formal flood engineering reports are commonly required for DAs in flood-affected areas.',
      },
      {
        q: 'Where do I get the official flood status for a Wentworth property?',
        a: 'A Section 10.7 Planning Certificate from Wentworth Shire Council is the authoritative source for flood status. This is mandatory in NSW conveyancing. Given Wentworth\'s high flood risk profile, obtaining this certificate before any property purchase is strongly recommended.',
      },
      {
        q: 'Can I build a granny flat on a Wentworth flood-affected property?',
        a: 'Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway. Given the extent of Wentworth\'s flood planning areas, many properties in the town area would require a DA with comprehensive flood risk assessment rather than a simple CDC.',
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
        a: 'The Clarence River is one of the largest catchments in NSW and creates significant flood risk across the Clarence Valley. The Clarence Valley LEP defines flood planning areas for Grafton, Maclean, Yamba, and surrounding townships. Use the checker to confirm your address\'s status.',
      },
      {
        q: 'What are the flood risks in Grafton and Maclean?',
        a: 'Grafton sits on the Clarence River floodplain and has a long history of major flood events. Maclean and the lower Clarence have additional flood risk from tidal and storm surge interaction. The 2022 floods were among the most damaging recorded, prompting updated flood studies.',
      },
      {
        q: 'Does Clarence Valley have detailed ARI flood data?',
        a: 'Clarence Valley\'s spatial data currently includes Probable Maximum Flood (PMF) extents. More detailed ARI scenario data (1%, 2%, 5% AEP) is being updated following the 2022 flood events. The statutory flood planning area boundaries are the key planning reference.',
      },
      {
        q: 'How do I get the official flood status for a Clarence Valley property?',
        a: 'A Section 10.7 Planning Certificate from Clarence Valley Council is the authoritative source. Given the extent of flood risk across the Clarence Valley, this certificate is especially important for any property near the Clarence River system.',
      },
      {
        q: 'Does flood zone status affect granny flat eligibility in Clarence Valley?',
        a: 'Yes. Under SEPP Housing 2021, flood control lots are excluded from the complying development pathway for secondary dwellings. Much of the lower Clarence Valley is in flood planning areas — check your address above, then verify CDC eligibility with the granny flat checker.',
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
        a: 'Forbes sits on the Lachlan River floodplain and is one of the most flood-prone towns in central western NSW. The Forbes LEP defines flood planning areas covering significant portions of the town. Use the checker above to confirm your address\'s status.',
      },
      {
        q: 'What is Forbes\'s flood history?',
        a: 'Forbes has experienced major flooding from the Lachlan River multiple times, including in 2016 and the catastrophic 2022 event which inundated large parts of the town. The 2022 floods were among the worst on record, prompting significant levee and drainage works.',
      },
      {
        q: 'How do flood controls affect development in Forbes?',
        a: 'Forbes has strict development controls for flood-prone land given its history of major events. Habitable floor levels, flood-compatible materials, and evacuation access are key requirements for development in flood planning areas.',
      },
      {
        q: 'Where do I get the official flood status for a Forbes property?',
        a: 'A Section 10.7 Planning Certificate from Forbes Shire Council is the authoritative source. Given Forbes\'s flood history, obtaining this certificate and reviewing the council\'s floodplain risk management plan before any purchase is strongly recommended.',
      },
      {
        q: 'Does flood risk affect granny flat eligibility in Forbes?',
        a: 'Under SEPP Housing 2021, flood control lots cannot use the complying development pathway. Given the extent of Forbes\'s flood planning areas, many properties would require a DA with flood impact assessment rather than a CDC for a secondary dwelling.',
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
        a: 'Yass Valley Council has defined flood planning areas for the Yass River and tributary areas under the Yass Valley LEP. Use the checker above to confirm whether your specific address falls within the mapped flood planning area.',
      },
      {
        q: 'What are the flood risks in Yass?',
        a: 'The Yass River through Yass township is the primary flood risk source. Low-lying areas near the river in central Yass are most susceptible to inundation. The Yass Valley Council\'s floodplain risk management plan covers these areas.',
      },
      {
        q: 'Does Yass Valley have detailed ARI flood data?',
        a: 'Yass Valley\'s spatial data currently includes Probable Maximum Flood (PMF) extents. The statutory flood planning area boundaries under the Yass Valley LEP are the primary planning reference for development assessment.',
      },
      {
        q: 'How do I get the official flood status for a Yass property?',
        a: 'A Section 10.7 Planning Certificate from Yass Valley Council is the authoritative source for flood status. This is required for conveyancing and discloses all statutory planning constraints including flood risk.',
      },
      {
        q: 'Can I build a granny flat on a flood-affected Yass Valley property?',
        a: 'Under SEPP Housing 2021, properties on flood control lots are excluded from the complying development (CDC) pathway. If your Yass Valley property is within the flood planning area, a secondary dwelling requires a DA with appropriate flood assessment.',
      },
    ],
  },
]

export const FLOOD_LGA_SLUG_MAP: Record<string, FloodLgaData> = Object.fromEntries(
  FLOOD_LGAS.map(lga => [lga.slug, lga])
)

import posthog from 'posthog-js';

// Track address search
export const trackAddressSearch = (address: string, council?: string, zone?: string) => {
  posthog.capture('address_search', {
    address,
    council: council || 'Unknown',
    zone: zone || 'Unknown'
  });
};

// Track provision view
export const trackProvisionView = (provisionId: number, topic: string, layer: string, council: string) => {
  posthog.capture('provision_view', {
    provisionId,
    topic,
    layer,
    council
  });
};

// Track PDF page view
export const trackPdfView = (provisionId: number, pdfUrl: string) => {
  posthog.capture('pdf_view', {
    provisionId,
    pdfUrl
  });
};

// Track topic filter
export const trackTopicFilter = (topic: string, resultCount: number, council: string) => {
  posthog.capture('topic_filter', {
    topic,
    resultCount,
    council
  });
};

// Track tab change
export const trackTabChange = (tab: 'sepp-lep' | 'dcp') => {
  posthog.capture('tab_change', {
    tab
  });
};

// Track zone info view
export const trackZoneInfoView = (zone: string, council: string) => {
  posthog.capture('zone_info_view', {
    zone,
    council
  });
};

// Track prospector bulk lot search execution (fires per successful search,
// i.e. on landing and on each filter change — funnel step after pageview)
export const trackProspectorSearch = (params: {
  lga: string;
  zone_codes: string[];
  has_heritage_filter: boolean;
  has_flood_filter: boolean;
  result_count: number;
  query_ms: number | null;
  page: number;
}) => {
  posthog.capture('prospector_search', params);
};

// Track prospector email capture (funnel conversion step: pageview ->
// prospector_search -> prospector_email_capture)
export const trackProspectorEmailCapture = (params: {
  lga: string;
  has_filters: boolean;
  role: string | null;
}) => {
  posthog.capture('prospector_email_capture', params);
};

// Track SEO funnel page CTA click
export const trackFunnelCta = (page: string, cta: string, destination: string) => {
  posthog.capture('funnel_cta_click', {
    page,
    cta,
    destination
  });
};

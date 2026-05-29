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

// Track SEO funnel page CTA click
export const trackFunnelCta = (page: string, cta: string, destination: string) => {
  posthog.capture('funnel_cta_click', {
    page,
    cta,
    destination
  });
};

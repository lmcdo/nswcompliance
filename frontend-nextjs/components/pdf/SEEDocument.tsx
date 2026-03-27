// SEE PDF Document — deterministic scaffold, 100% data-driven
// No AI, no hardcoded LGA names, no hardcoded zone lists beyond domain logic

import { Document } from '@react-pdf/renderer';
import { SEEDocumentData } from '@/lib/see/types';
import { buildSEEData } from '@/lib/see/section-aggregation';
import { Page1Cover } from './see-pages/Page1Cover';
import { Page2SiteContext } from './see-pages/Page2SiteContext';
import { Page3Pathway } from './see-pages/Page3Pathway';
import { Page4Dcp } from './see-pages/Page4Dcp';
import { Page5Environmental } from './see-pages/Page5Environmental';
import { Page6Conclusion } from './see-pages/Page6Conclusion';

export function SEEDocument({ data }: { data: SEEDocumentData }) {
  const computed = buildSEEData(data);

  return (
    <Document>
      <Page1Cover computed={computed} />
      <Page2SiteContext computed={computed} />
      <Page3Pathway computed={computed} />
      <Page4Dcp computed={computed} />
      <Page5Environmental computed={computed} />
      <Page6Conclusion computed={computed} />
    </Document>
  );
}

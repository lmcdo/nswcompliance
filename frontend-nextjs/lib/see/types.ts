// SEE Document Types — deterministic, data-driven only

import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';

export interface SEEDocumentData {
  property: PropertyContext;
  development_description: string;
  annotated_provisions: ProvisionForPDF[];  // provisions with da_status set
  all_provisions: ProvisionForPDF[];
  generated_date: string;
}

// SEE Document Types — deterministic, data-driven only

import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';
import type { IntakeAnswers } from '@/lib/see/intake';

export interface SEEDocumentData {
  property: PropertyContext;
  development_description: string;
  annotated_provisions: ProvisionForPDF[];  // provisions with da_status set
  all_provisions: ProvisionForPDF[];
  generated_date: string;
  /** Confirmed intake answers — used for the audit trail on the SEE cover page */
  intake_answers?: IntakeAnswers;
  /** Client name or site reference — appears on SEE cover */
  client_ref?: string;
  /** Consultant or firm name preparing the document */
  prepared_by?: string;
  /** Pre-built natural-language introduction paragraph */
  see_intro?: string;
}

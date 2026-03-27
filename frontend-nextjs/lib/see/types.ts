// SEE Document Types — deterministic, data-driven only

import { PropertyContext, ProvisionForPDF } from '@/lib/pdf/types';
import type { IntakeAnswers } from '@/lib/see/intake';

/** Approval pathway determination with legislative basis and required specialist reports. */
export interface PathwayDetermination {
  /** e.g. 'Development Application (DA)' or 'Complying Development (CDC)' */
  pathway: string;
  /** Human-readable reason e.g. 'Heritage conservation area — CDC and exempt development restricted' */
  reason: string;
  /** Legislative basis for the determination e.g. 'SEPP (Exempt & Complying Development Codes) 2008 cl.1.17' */
  legislative_basis: string;
  /** Specialist reports required for lodgement e.g. ['Heritage Impact Statement', 'BASIX Certificate'] */
  required_reports: string[];
  /** Planning caveats e.g. accelerated TOD rezoning notices */
  caveats?: string[];
}

/** A single SEPP control row for assessment in the SEE. */
export interface SeppAssessableControl {
  /** Instrument name e.g. 'SEPP (Sustainable Buildings) 2022' */
  instrument: string;
  /** Control name e.g. 'BASIX — Water Efficiency' */
  control: string;
  /** Specific requirement text e.g. 'Water target: 40% reduction from baseline' */
  requirement: string;
  /** Clause reference e.g. 'BASIX Certificate — NSW Planning Portal' */
  clause: string;
  status: 'complies' | 'varies' | 'not_applicable' | 'pending';
  notes?: string;
}

/** A single LEP standard row for assessment in the SEE. */
export interface LepAssessableStandard {
  /** Clause number e.g. '4.3' */
  clause: string;
  /** Control name e.g. 'Height of Buildings' */
  control: string;
  /** Requirement text e.g. 'Maximum 10m' */
  requirement: string;
  /** Proposal value if known e.g. 'Proposed: 6.2m' — filled by planner */
  proposal?: string;
  status: 'complies' | 'varies' | 'not_applicable' | 'pending';
  notes?: string;
  /** Source citation e.g. 'Inner West LEP 2022 Clause 4.3' */
  source: string;
}

export interface TopicAssertion {
  topic: string;
  reason: string;
}

/** Chapter-level assertion — planner dismissed an entire DCP chapter by its actual document reference. */
export interface ChapterAssertion {
  /** The partId used as grouping key e.g. 'chapter-b3-general-development' or 'B7' */
  chapter_key: string;
  /** Short label shown in SEE table e.g. 'Chapter B3' or 'B7' */
  chapter_label: string;
  /** Chapter description e.g. 'General Development Controls' or 'Transport' */
  chapter_desc: string;
  /** One-sentence reason for non-applicability */
  reason: string;
}

/** A single DCP section assessment for the section-level model. */
export interface SectionAssessment {
  /** Section key — format: `${partKey}::${sectionNumber}` e.g. 'Part 1::2.1' */
  section_key: string;
  section_title: string | null;
  status: 'complies' | 'varies' | 'not_applicable' | 'flagged' | null;
  narrative: string | null;
  /** Leading provision text(s) from this section — shown as DCP requirement in compliance table */
  key_provisions?: string[];
}

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
  /** Approval pathway determination with legislative basis and required reports */
  pathway_determination?: PathwayDetermination;
  /** SEPP controls applicable to this assessment (BASIX, TOD parking, etc.) */
  sepp_assessable_controls?: SeppAssessableControl[];
  /** LEP development standards applicable to this assessment (height, FSR, heritage, etc.) */
  lep_assessable_standards?: LepAssessableStandard[];
  /** Topic-level assertions — planner-dismissed topics with one-sentence reasons (Schedule B, fallback) */
  topic_assertions?: TopicAssertion[];
  /** Chapter-level assertions — planner-dismissed DCP chapters by actual document reference (Schedule B, preferred) */
  chapter_assertions?: ChapterAssertion[];
  /** Selected ancillary works — used to flag works selected but with no provisions for the dev type */
  ancillary_works?: string[];
  /** R2 public PDF URL for deep-linking provisions to DCP source pages */
  council_pdf_url?: string;
  /** Section-level assessment responses (section-level DA model) */
  section_responses?: SectionAssessment[];
  /** All unique DCP sections in scope — used for completeness tracking in the PDF */
  section_scope?: { section_key: string; section_title: string | null }[];
}

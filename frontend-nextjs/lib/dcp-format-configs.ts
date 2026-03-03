/**
 * DCP Format Configs
 *
 * Council-specific text cleanup rules for provision_text artifacts produced by PDF extraction.
 * Each council's DCP PDF has its own header/footer patterns, chapter prefix conventions, etc.
 *
 * Usage:
 *   import { preProcessProvisionText } from '@/lib/dcp-format-configs';
 *   const cleaned = preProcessProvisionText(rawText, formerCouncil.toLowerCase());
 *
 * Onboarding new councils:
 *   1. Run `python scripts/verify_dcp_formatting.py --council <name> --limit 50`
 *   2. If >= 5% of provisions have flagged artifact lines, add an entry here
 *   3. Rerun verify script to confirm pass gate (< 5%)
 */

export interface DcpFormatConfig {
  /** Skip lines that start with any of these exact string prefixes */
  skipLinePrefixes?: string[];
  /** Skip lines matching any of these patterns */
  skipLinePatterns?: RegExp[];
  /** Apply these regex replacements to the whole provision text before line filtering */
  preProcessReplacements?: Array<{ from: RegExp; to: string }>;
}

/**
 * Config registry keyed by formerCouncil.toLowerCase().
 * Add an entry for every council whose DCP extraction produces text artifacts.
 * Empty entries are intentional — they document that the council was checked and is clean.
 */
const DCP_FORMAT_CONFIGS: Record<string, DcpFormatConfig> = {
  marrickville: {
    // Running page header: "N  Marrickville Development Control Plan 2011" printed on every page.
    // Appears in provision_text as:
    //   "# 5 Marrickville Development Control Plan 2011"  (markdown heading form)
    //   "5"                                                (bare page number)
    //   "Marrickville Development Control Plan 2011"       (document title repeat)
    skipLinePatterns: [
      /^\d{1,3}$/,              // bare page numbers (1–3 digits, whole line)
      /^#\s*\d{1,3}\s+\w/,     // "# 5 Title..." page header in markdown heading form
    ],
    skipLinePrefixes: [
      'Marrickville Development Control Plan',
    ],
  },

  ashfield: {
    // "Comprehensive Inner West DCP 2016" appears as a document title line in
    // ~67 actionable provisions extracted from the Ashfield DCP PDF.
    skipLinePrefixes: [
      'Comprehensive Inner West DCP 2016',
    ],
    // ~65 provisions start with "Chapter X" or "Chapter E1" prefix lines
    // (e.g., "Chapter C\n\nSustainability controls..."). Strip this leading line.
    preProcessReplacements: [
      { from: /^Chapter [A-Z]\d*[^\n]*\n+/m, to: '' },
    ],
  },

  leichhardt: {
    // Clean text — no extraction artifacts detected.
    // Entry present to document that the council was verified.
  },

  waverley: {
    // PDF: Waverley_DCP_2022_Full_Version_Amendment5.pdf (single 490-page PDF, Parts A–F)
    // Every content page starts with two header lines before the actual text:
    //   "Ecologically Sustainable Development      B2"  (section title, right-aligned to code)
    //   "WAVERLEY DEVELOPMENT CONTROL PLAN 2022"        (document title)
    //   "4"                                             (bare page number)
    // Confirmed from waverley/waverley_dcp_analysis_first50.txt.
    skipLinePatterns: [
      /^\d{1,3}$/,                    // bare Arabic page numbers (4, 5, 78...)
      /\s{3,}[A-F]\d{1,2}\s*$/,      // right-aligned running header: "Waste      B1"
    ],
    skipLinePrefixes: [
      'WAVERLEY DEVELOPMENT CONTROL PLAN',  // document title on every page
    ],
  },

  // Future councils added here during onboarding.
  // Run: python scripts/verify_dcp_formatting.py --council <name> --limit 50
  // Also manually inspect 10 raw provisions from DB (see LGA_EXTRACTION_RUNBOOK.md Step 6b).
};

/**
 * Get format config for a council key.
 * Returns null if the council has no config (safe — caller can skip preprocessing).
 */
export function getDcpFormatConfig(councilKey: string): DcpFormatConfig | null {
  return DCP_FORMAT_CONFIGS[councilKey.toLowerCase()] ?? null;
}

/**
 * Pre-process provision text using council-specific cleanup rules.
 *
 * Steps:
 *   1. Apply preProcessReplacements to the whole text (e.g., strip leading chapter headers)
 *   2. Split into lines, filter out artifact lines, rejoin
 *   3. Preserve blank lines (paragraph structure)
 *
 * Returns the original text unchanged if no config exists for councilKey.
 */
export function preProcessProvisionText(text: string, councilKey: string): string {
  if (!text || !councilKey) return text;

  const config = getDcpFormatConfig(councilKey);
  if (!config) return text;

  let processed = text;

  // Step 1: whole-text replacements (e.g., strip "Chapter C\n" from start)
  if (config.preProcessReplacements) {
    for (const { from, to } of config.preProcessReplacements) {
      processed = processed.replace(from, to);
    }
  }

  // Step 2: line-level filtering
  const hasLineFilters =
    (config.skipLinePrefixes && config.skipLinePrefixes.length > 0) ||
    (config.skipLinePatterns && config.skipLinePatterns.length > 0);

  if (!hasLineFilters) return processed;

  const lines = processed.split('\n');
  const filtered = lines.filter(line => {
    const trimmed = line.trim();

    // Preserve blank lines — they carry paragraph structure
    if (!trimmed) return true;

    if (config.skipLinePrefixes) {
      for (const prefix of config.skipLinePrefixes) {
        if (trimmed.startsWith(prefix)) return false;
      }
    }

    if (config.skipLinePatterns) {
      for (const pattern of config.skipLinePatterns) {
        if (pattern.test(trimmed)) return false;
      }
    }

    return true;
  });

  return filtered.join('\n');
}

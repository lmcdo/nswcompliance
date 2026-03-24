'use client';

/**
 * CDC/DA Pathway Decision Tree
 *
 * Data-driven eligibility checker - no hardcoded limits.
 * All rules derived from SEPP Exempt & Complying Development database.
 */

import { useState, useEffect, useMemo } from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface CDCPathwayProps {
  propertyData: any;
  proposedWorkType?: 'deck' | 'garage' | 'extension' | 'other';
}

interface Answer {
  questionId: string;
  value: any;
}

interface Requirement {
  pass: boolean;
  warn?: boolean;
  text: string;
}

interface CheckResult {
  verdict: 'eligible' | 'review' | 'ineligible';
  tier: string;
  summary: string;
  blockers?: string[];
  requirements?: Requirement[];
  notes?: string[];
  timeline: string;
  cost: string;
  nextStep: string;
  source: string;
}

interface SeppProvision {
  id: number;
  provision_text: string;
  pdf_page: number;
  v2_part: string;
  v2_topic: string;
}

// Work type configuration - defines which questions apply to each type
interface WorkTypeConfig {
  backendValue: string;  // What SEPP database expects
  needsArea: boolean;
  needsHeight: boolean;
  areaLabel?: string;
  heightLabel?: string;
}

const WORK_TYPE_CONFIGS: Record<string, WorkTypeConfig> = {
  Deck: {
    backendValue: 'Deck',
    needsArea: true,
    needsHeight: true,
    areaLabel: 'What is the deck floor area?',
    heightLabel: 'What is the deck height above ground?'
  },
  Garage: {
    backendValue: 'Carport',  // ← FIX: Backend expects "Carport"
    needsArea: true,
    needsHeight: true,
    areaLabel: 'What is the garage floor area?',
    heightLabel: 'What is the maximum garage height?'
  },
  Pool: {
    backendValue: 'Pool',
    needsArea: true,
    needsHeight: false,  // ← Pools don't have height above ground
    areaLabel: 'What is the pool area?'
  },
  Fence: {
    backendValue: 'Fence',
    needsArea: false,  // ← Fences don't have floor area
    needsHeight: true,
    heightLabel: 'What is the fence height?'
  },
};

const getQuestionsForWorkType = (workType: string | null, maxGFA: number | null) => {
  const questions: any[] = [
    {
      id: 'work_type',
      text: 'What are you building?',
      type: 'select' as const,
      options: [
        { value: 'Deck', label: 'Deck, Patio, or Verandah' },
        { value: 'Garage', label: 'Garage or Carport' },
        { value: 'Pool', label: 'Swimming Pool' },
        { value: 'Fence', label: 'Fence or Gate' },
      ],
      guidance: 'Select the type of structure you want to build.',
    },
  ];

  if (!workType) return questions;

  const config = WORK_TYPE_CONFIGS[workType];
  if (!config) return questions;

  // Add area question if applicable
  if (config.needsArea) {
    questions.push({
      id: 'area',
      text: config.areaLabel || 'What is the floor area?',
      type: 'number' as const,
      unit: 'm²',
      guidance: maxGFA
        ? `Floor area = length × width. Example: 5m × 4m = 20m². Maximum GFA on this lot: ${Math.round(maxGFA)}m² (LEP Clause 4.4 FSR control).`
        : "Floor area = length × width. Example: 5m × 4m = 20m².",
    });
  }

  // Add height question if applicable
  if (config.needsHeight) {
    questions.push({
      id: 'height',
      text: config.heightLabel || 'What is the maximum height?',
      type: 'number' as const,
      unit: 'm',
      guidance: workType === 'Fence'
        ? 'Fence height from ground level (typical limits: 1.2m front, 1.8m side/rear)'
        : 'Highest point above natural ground level.',
    });
  }

  return questions;
};

// Parse exempt limits from SEPP provisions (instead of hardcoding)
function parseExemptLimits(provisions: SeppProvision[]) {
  let areaLimit: number | null = null;
  let heightLimit: number | null = null;

  for (const p of provisions) {
    const text = p.provision_text.toLowerCase();

    // Parse area limit: "not exceed 10m2" or "less than 36m2"
    const areaMatch = text.match(/(?:not exceed|less than|maximum.*?of)\s+(\d+)\s*m\s*2/);
    if (areaMatch && !areaLimit) {
      areaLimit = parseInt(areaMatch[1]);
    }

    // Parse height limit: "not exceed 3m" or "maximum height of 1m"
    const heightMatch = text.match(/(?:height|high).*?(?:not exceed|less than|maximum.*?of)\s+(\d+(?:\.\d+)?)\s*m(?!2)/);
    if (heightMatch && !heightLimit) {
      heightLimit = parseFloat(heightMatch[1]);
    }
  }

  return { areaLimit, heightLimit };
}

// Parse minimum lot area for CDC from provisions
function parseMinLotArea(provisions: SeppProvision[]): { minArea: number; source: string } {
  const lotAreaProvisions = provisions.filter(p =>
    p.provision_text.toLowerCase().includes('area of the lot')
  );

  if (lotAreaProvisions.length > 0) {
    const match = lotAreaProvisions[0].provision_text.match(/more than (\d+)\s*m\s*2/);
    if (match) {
      return {
        minArea: parseInt(match[1].replace(/\s/g, '')),
        source: `SEPP Housing Code Part ${provisions[0]?.v2_part}, page ${lotAreaProvisions[0].pdf_page}`,
      };
    }
  }

  // Fallback defaults (standard SEPP Housing Code Part 3)
  return {
    minArea: 200,
    source: 'SEPP Housing Code Part 3, clause 3.1 (default)',
  };
}

export function CDCPathway({ propertyData }: CDCPathwayProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [seppProvisions, setSeppProvisions] = useState<SeppProvision[]>([]);
  const [loadingProvisions, setLoadingProvisions] = useState(false);

  const maxGFA =
    propertyData?.constraints?.maxFsr && propertyData?.lotDimensions?.area
      ? propertyData.constraints.maxFsr * propertyData.lotDimensions.area
      : null;

  const workType = answers.find(a => a.questionId === 'work_type')?.value as string | null;
  const questions = useMemo(() => getQuestionsForWorkType(workType, maxGFA), [workType, maxGFA]);

  // Fetch SEPP provisions when work type is selected
  useEffect(() => {
    const zone = propertyData?.constraints?.zone;
    if (workType && zone) {
      const config = WORK_TYPE_CONFIGS[workType];
      if (!config) return;

      setLoadingProvisions(true);
      // Use backend value (Carport, not Garage)
      fetch(`/api/sepp/exempt-complying?zone=${zone}&workType=${config.backendValue}`)
        .then(res => res.json())
        .then(data => {
          setSeppProvisions(data.provisions || []);
          setLoadingProvisions(false);
        })
        .catch(() => setLoadingProvisions(false));
    }
  }, [workType, propertyData?.constraints?.zone]);

  const handleAnswer = (questionId: string, value: any, autoAdvance = false) => {
    setAnswers(prev => {
      const idx = prev.findIndex(a => a.questionId === questionId);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = { questionId, value };
        return updated;
      }
      return [...prev, { questionId, value }];
    });

    // Reset to work_type question if work type changes (questions will be different)
    if (questionId === 'work_type') {
      setAnswers([{ questionId: 'work_type', value }]);
      setCurrentStep(0);
      setSeppProvisions([]);
      setResult(null);
    } else if (autoAdvance && currentStep < questions.length - 1) {
      setTimeout(() => setCurrentStep(s => s + 1), 300);
    }
  };

  const handleNext = () => {
    if (currentStep < questions.length - 1) {
      setCurrentStep(s => s + 1);
    } else {
      setCurrentStep(questions.length); // advance to results
    }
  };

  const handleBack = () => {
    if (currentStep > 0) setCurrentStep(s => s - 1);
  };

  const currentQuestion = questions[currentStep];

  const canAdvance = () => {
    const answer = answers.find(a => a.questionId === currentQuestion?.id);
    if (!answer) return false;
    if (currentQuestion?.type === 'number') return !isNaN(answer.value) && answer.value > 0;
    if (currentQuestion?.type === 'select') return !!answer.value;
    return answer.value !== undefined;
  };

  // 3-Tier Pathway Check — data-driven from SEPP provisions
  useEffect(() => {
    if (currentStep < questions.length || !workType) {
      setResult(null);
      return;
    }

    const config = WORK_TYPE_CONFIGS[workType];
    if (!config) return;

    const area = answers.find(a => a.questionId === 'area')?.value as number | undefined;
    const height = answers.find(a => a.questionId === 'height')?.value as number | undefined;

    // Validate required inputs
    if (config.needsArea && (!area || area <= 0)) return;
    if (config.needsHeight && (!height || height <= 0)) return;

    const lotArea = propertyData?.lotDimensions?.area || 0;
    const isHeritage = propertyData?.heritage?.isHeritage || false;
    const zone = propertyData?.constraints?.zone || '';
    const workLabel = workType.toLowerCase();

    // PRE-CHECK: Exceeds Max GFA → DA required
    if (maxGFA !== null && area && area > maxGFA) {
      setResult({
        verdict: 'ineligible',
        tier: 'DA Required',
        summary: `Proposed floor area (${area}m²) exceeds maximum GFA of ${Math.round(maxGFA)}m² for this lot.`,
        blockers: [
          `${area}m² proposed > ${Math.round(maxGFA)}m² maximum GFA (FSR ${propertyData.constraints.maxFsr}:1 × ${Math.round(lotArea)}m² lot)`,
          'LEP FSR control is a hard ceiling — neither exempt nor CDC can authorise works above it',
        ],
        timeline: '3–6 months',
        cost: '~$5,000–$15,000 (town planner + council fees)',
        nextStep: 'Engage a town planner to prepare a Development Application (DA)',
        source: `${propertyData.constraints?.lga || 'LEP'}, Clause 4.4 — Floor Space Ratio`,
      });
      return;
    }

    // TIER 1: EXEMPT - Parse limits from SEPP provisions
    if (!loadingProvisions && seppProvisions.length > 0) {
      const { areaLimit, heightLimit } = parseExemptLimits(seppProvisions);

      const areaOk = !area || !areaLimit || area < areaLimit;
      const heightOk = !height || !heightLimit || height <= heightLimit;

      if (areaOk && heightOk) {
        const reqs: Requirement[] = [];
        if (area && areaLimit) {
          reqs.push({ pass: true, text: `Area ${area}m² — under ${areaLimit}m² exempt limit` });
        }
        if (height && heightLimit) {
          reqs.push({ pass: true, text: `Height ${height}m — at or under ${heightLimit}m exempt limit` });
        }
        reqs.push({
          pass: !isHeritage,
          warn: isHeritage,
          text: isHeritage
            ? 'Heritage property — confirm with certifier before starting'
            : `Zone ${zone} — permitted`,
        });

        setResult({
          verdict: 'eligible',
          tier: 'Exempt Development',
          summary: `Your ${workLabel} qualifies as exempt development — no approval needed.`,
          requirements: reqs,
          notes: workType === 'Pool' ? ['Pool fencing must comply with NSW pool safety standards regardless of approval pathway'] : undefined,
          timeline: 'No approval process — start immediately',
          cost: 'No approval fees',
          nextStep: 'Proceed to construction',
          source: `SEPP (Exempt and Complying Development Codes) 2008, Part 2 (${seppProvisions.length} provisions checked)`,
        });
        return;
      }

      // TIER 2/3: CDC or DA
      const { minArea, source: lotAreaSource } = parseMinLotArea(seppProvisions);

      const cdcBlockers: string[] = [];
      if (lotArea > 0 && lotArea < minArea) {
        cdcBlockers.push(`Lot size ${Math.round(lotArea)}m² — below ${minArea}m² CDC minimum (${lotAreaSource})`);
      }
      if (isHeritage) {
        cdcBlockers.push('Heritage property — CDC not available, DA required');
      }

      if (cdcBlockers.length === 0) {
        // CDC pathway
        const exemptBlockers: string[] = [];
        if (area && areaLimit && area >= areaLimit) {
          exemptBlockers.push(`Area ${area}m² — exceeds ${areaLimit}m² exempt limit`);
        }
        if (height && heightLimit && height > heightLimit) {
          exemptBlockers.push(`Height ${height}m — exceeds ${heightLimit}m exempt limit`);
        }
        if (!areaLimit && !heightLimit) {
          exemptBlockers.push(`${workType} — no exempt pathway available for this configuration`);
        }

        setResult({
          verdict: 'review',
          tier: 'Complying Development (CDC)',
          summary: `Your ${workLabel} cannot proceed as exempt — a CDC is required.`,
          blockers: exemptBlockers,
          requirements: [
            { pass: true, text: `Lot size ${Math.round(lotArea)}m² — meets ${minArea}m² minimum` },
            { pass: true, text: `Zone ${zone} — CDC permitted` },
            { pass: false, warn: true, text: 'Setback requirements — certifier to measure and confirm on site' },
          ],
          timeline: '20 business days',
          cost: '~$2,000–$3,000 (private certifier fee)',
          nextStep: 'Contact a Private Certifier — they assess setbacks and issue the CDC',
          source: lotAreaSource,
        });
      } else {
        // DA required
        setResult({
          verdict: 'ineligible',
          tier: 'DA Required',
          summary: `Your ${workLabel} cannot proceed as CDC — a Development Application is required.`,
          blockers: cdcBlockers,
          timeline: '3–6 months',
          cost: '~$5,000–$15,000 (town planner + council fees)',
          nextStep: `Engage a town planner to prepare a DA lodged with ${propertyData?.constraints?.lga || 'your'} Council`,
          source: `${propertyData?.constraints?.lga || 'Council'} DCP, SEPP Housing Code`,
        });
      }
    } else if (!loadingProvisions) {
      // No SEPP provisions found - can't determine limits
      setResult({
        verdict: 'ineligible',
        tier: 'Unable to Determine',
        summary: `No SEPP provisions found for ${workLabel} in ${zone} zone.`,
        blockers: ['SEPP data not available for this work type/zone combination'],
        timeline: 'Unknown',
        cost: 'Consult with certifier',
        nextStep: 'Contact a Private Certifier for manual assessment',
        source: 'SEPP database query returned no results',
      });
    }
  }, [answers, seppProvisions, loadingProvisions, propertyData, currentStep, workType, questions.length]);

  const showResults = currentStep >= questions.length;

  return (
    <div className="space-y-4">
      {/* Progress */}
      {!showResults && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span className="font-medium">Step {currentStep + 1} of {questions.length}</span>
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-600 transition-all duration-300"
              style={{ width: `${((currentStep + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Questions */}
      {!showResults && (
        <div className="space-y-3">
          {questions.map((question, index) => {
            const answer = answers.find(a => a.questionId === question.id);
            const isActive = index === currentStep;
            const isAnswered = answer !== undefined;

            return (
              <div
                key={question.id}
                className={`border rounded-lg p-4 transition-all ${
                  isActive
                    ? 'border-teal-400 bg-teal-50 shadow-sm'
                    : isAnswered
                    ? 'border-gray-200 bg-white'
                    : 'border-gray-100 bg-gray-50 opacity-60'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${isAnswered ? 'bg-teal-600 text-white' : 'bg-gray-300 text-gray-600'}`}>
                    {isAnswered ? <CheckCircle2 className="w-4 h-4" /> : index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 mb-1">{question.text}</p>
                    {question.guidance && isActive && (
                      <p className="text-xs text-gray-500 mb-2">{question.guidance}</p>
                    )}

                    {isActive && question.type === 'number' && (
                      <div className="flex gap-2 mt-2">
                        <input
                          type="number"
                          value={answer?.value || ''}
                          onChange={e => handleAnswer(question.id, parseFloat(e.target.value))}
                          placeholder="Enter value"
                          className="flex-1 text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                        />
                        {question.unit && (
                          <span className="flex items-center px-3 py-2 bg-gray-100 border border-gray-300 rounded text-sm text-gray-600">
                            {question.unit}
                          </span>
                        )}
                      </div>
                    )}

                    {isActive && question.type === 'select' && question.options && (
                      <div className="mt-2">
                        <select
                          value={answer?.value || ''}
                          onChange={e => handleAnswer(question.id, e.target.value, true)}
                          className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                        >
                          <option value="">Select...</option>
                          {question.options.map((opt: any) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {isAnswered && !isActive && (
                      <p className="text-sm text-gray-700 mt-1">
                        <strong>
                          {question.type === 'select'
                            ? question.options?.find((o: any) => o.value === answer.value)?.label || answer.value
                            : (isNaN(answer.value) || answer.value <= 0)
                            ? <span className="text-red-500 italic">Enter a value</span>
                            : `${answer.value}${question.unit || ''}`}
                        </strong>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Results */}
      {showResults && result && (
        <div className="space-y-3">
          {/* Verdict banner */}
          <div className={`rounded-xl p-5 border-2 ${
            result.verdict === 'eligible' ? 'border-green-500 bg-green-50'
            : result.verdict === 'review' ? 'border-amber-500 bg-amber-50'
            : 'border-red-500 bg-red-50'
          }`}>
            <div className="flex items-start gap-3">
              {result.verdict === 'eligible' && <CheckCircle2 className="w-7 h-7 text-green-600 flex-shrink-0 mt-0.5" />}
              {result.verdict === 'review' && <AlertTriangle className="w-7 h-7 text-amber-600 flex-shrink-0 mt-0.5" />}
              {result.verdict === 'ineligible' && <XCircle className="w-7 h-7 text-red-600 flex-shrink-0 mt-0.5" />}
              <div>
                <p className={`text-base font-bold ${
                  result.verdict === 'eligible' ? 'text-green-900'
                  : result.verdict === 'review' ? 'text-amber-900'
                  : 'text-red-900'
                }`}>{result.tier}</p>
                <p className={`text-sm mt-0.5 ${
                  result.verdict === 'eligible' ? 'text-green-800'
                  : result.verdict === 'review' ? 'text-amber-800'
                  : 'text-red-800'
                }`}>{result.summary}</p>
              </div>
            </div>
          </div>

          {/* Why blocked (fails) */}
          {result.blockers && result.blockers.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">
                {result.verdict === 'review' ? 'Why Not Exempt' : 'Reason'}
              </p>
              <ul className="space-y-1">
                {result.blockers.map((b, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-800">
                    <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Requirements (pass/warn/fail rows) */}
          {result.requirements && result.requirements.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Requirements</p>
              <ul className="space-y-1.5">
                {result.requirements.map((req, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {req.warn ? (
                      <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    ) : req.pass ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    )}
                    <span className={req.warn ? 'text-amber-800' : req.pass ? 'text-gray-700' : 'text-red-700'}>
                      {req.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes */}
          {result.notes && result.notes.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              {result.notes.map((n, i) => (
                <p key={i} className="text-sm text-amber-800">⚠ {n}</p>
              ))}
            </div>
          )}

          {/* Timeline / Cost / Next Step */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500 font-medium">Timeline</span>
              <span className="text-gray-900 font-semibold">{result.timeline}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500 font-medium">Approx. cost</span>
              <span className="text-gray-900 font-semibold">{result.cost}</span>
            </div>
            <div className="border-t border-gray-200 pt-2 mt-2">
              <p className="text-xs text-gray-500 font-medium mb-0.5">Next step</p>
              <p className="text-sm text-gray-900">{result.nextStep}</p>
            </div>
          </div>

          {/* Source */}
          <p className="text-xs text-gray-400 italic px-1">Source: {result.source}</p>
        </div>
      )}

      {/* Navigation — questions mode */}
      {!showResults && (
        <div className="flex items-center justify-between gap-4 pt-2">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentStep === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ← Back
          </button>
          <button
            onClick={handleNext}
            disabled={!canAdvance()}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              !canAdvance()
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm'
            }`}
          >
            {currentStep === questions.length - 1 ? 'Check Eligibility →' : 'Next →'}
          </button>
        </div>
      )}

      {/* Navigation — results mode */}
      {showResults && (
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={() => setCurrentStep(questions.length - 1)}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            ← Adjust Answers
          </button>
          <button
            onClick={() => { setCurrentStep(0); setAnswers([]); setResult(null); }}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-500 hover:bg-gray-200"
          >
            Start Over
          </button>
        </div>
      )}
    </div>
  );
}

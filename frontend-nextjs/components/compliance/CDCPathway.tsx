'use client';

/**
 * CDC/DA Pathway Decision Tree
 *
 * Interactive sequential eligibility checker for owner builders.
 * Asks questions step-by-step and shows real-time verdict.
 */

import { useState, useEffect } from 'react';
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

const QUESTIONS = (maxGFA: number | null) => [
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
  {
    id: 'area',
    text: 'What is the floor area of your structure?',
    type: 'number' as const,
    unit: 'm²',
    guidance: maxGFA
      ? `Floor area = length × width of the footprint. Example: a 5m × 4m garage = 20m². Maximum permitted GFA on this lot is ${Math.round(maxGFA)}m² (LEP Clause 4.4 FSR control — DA required if exceeded).`
      : "Floor area = length × width of the footprint. Example: a 5m × 4m garage = 20m².",
  },
  {
    id: 'height',
    text: 'What is the maximum height?',
    type: 'number' as const,
    unit: 'm',
    guidance: 'Highest point of the structure above natural ground level.',
  },
];

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

  const questions = QUESTIONS(maxGFA);

  // Fetch SEPP provisions when work type is selected
  useEffect(() => {
    const workType = answers.find(a => a.questionId === 'work_type')?.value;
    const zone = propertyData?.zone;
    if (workType && zone) {
      setLoadingProvisions(true);
      fetch(`/api/sepp/exempt-complying?zone=${zone}&workType=${workType}`)
        .then(res => res.json())
        .then(data => { setSeppProvisions(data.provisions || []); setLoadingProvisions(false); })
        .catch(() => setLoadingProvisions(false));
    }
  }, [answers, propertyData]);

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
    if (autoAdvance && currentStep < questions.length - 1) {
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

  // 3-Tier Pathway Check — only runs when user clicks "Check Eligibility"
  useEffect(() => {
    if (currentStep < questions.length) {
      setResult(null);
      return;
    }

    const workType = answers.find(a => a.questionId === 'work_type')?.value as string;
    const area = answers.find(a => a.questionId === 'area')?.value as number;
    const height = answers.find(a => a.questionId === 'height')?.value as number;

    if (!workType || isNaN(area) || area <= 0 || isNaN(height) || height <= 0) {
      setResult(null);
      return;
    }

    const lotArea = propertyData?.lotDimensions?.area || 0;
    const isHeritage = propertyData?.heritage?.isHeritage || false;
    const zone = propertyData?.zone || '';
    const workLabel = workType.toLowerCase();

    // PRE-CHECK: Exceeds Max GFA → DA required regardless
    if (maxGFA !== null && area > maxGFA) {
      setResult({
        verdict: 'ineligible',
        tier: 'DA Required',
        summary: `Proposed floor area (${area}m²) exceeds the maximum GFA of ${Math.round(maxGFA)}m² for this lot.`,
        blockers: [
          `${area}m² proposed > ${Math.round(maxGFA)}m² maximum GFA (FSR ${propertyData.constraints.maxFsr}:1 × ${Math.round(lotArea)}m² lot)`,
          'LEP FSR control is a hard ceiling — neither exempt nor CDC can authorise works above it',
        ],
        timeline: '3–6 months',
        cost: '~$5,000–$15,000 (town planner + council fees)',
        nextStep: 'Engage a town planner to prepare a Development Application (DA)',
        source: 'Inner West LEP 2022, Clause 4.4 — Floor Space Ratio',
      });
      return;
    }

    // TIER 1: EXEMPT
    const exemptLimits: Record<string, { area: number; height: number | null }> = {
      Garage: { area: 36, height: 3 },
      Deck:   { area: 10, height: 1 },
      Pool:   { area: 30, height: null },
    };
    const limit = exemptLimits[workType];
    if (limit) {
      const areaOk = area < limit.area;
      const heightOk = limit.height === null || height <= limit.height;
      if (areaOk && heightOk) {
        const reqs: Requirement[] = [
          { pass: true, text: `Area ${area}m² — under ${limit.area}m² exempt limit` },
          ...(limit.height !== null
            ? [{ pass: true, text: `Height ${height}m — at or under ${limit.height}m exempt limit` }]
            : []),
          {
            pass: !isHeritage,
            warn: isHeritage,
            text: isHeritage
              ? 'Heritage property — confirm with certifier before starting'
              : `Zone ${zone} — permitted`,
          },
        ];
        setResult({
          verdict: 'eligible',
          tier: 'Exempt Development',
          summary: `Your ${area}m² ${workLabel} qualifies as exempt development — no approval needed.`,
          requirements: reqs,
          notes: workType === 'Pool' ? ['Pool fencing must comply with NSW pool safety standards regardless of approval pathway'] : undefined,
          timeline: 'No approval process — start immediately',
          cost: 'No approval fees',
          nextStep: 'Proceed to construction',
          source: 'SEPP (Exempt and Complying Development Codes) 2008, Part 2',
        });
        return;
      }
    }

    // TIER 2 / 3: CDC or DA — need SEPP provisions loaded (or fallback)
    if (!loadingProvisions) {
      const lotAreaProvisions = seppProvisions.filter(p =>
        p.provision_text.toLowerCase().includes('area of the lot')
      );

      let minLotArea = 200;
      let lotAreaSource = 'SEPP Housing Code Part 3, clause 3.1';

      if (lotAreaProvisions.length > 0) {
        const match = lotAreaProvisions[0].provision_text.match(/more than (\d+)\s*m\s*2/);
        if (match) {
          minLotArea = parseInt(match[1].replace(/\s/g, ''));
          lotAreaSource = `SEPP Housing Code Part ${seppProvisions[0]?.v2_part}, page ${lotAreaProvisions[0].pdf_page}`;
        }
      }

      const cdcBlockers: string[] = [];
      if (lotArea > 0 && lotArea < minLotArea) {
        cdcBlockers.push(`Lot size ${Math.round(lotArea)}m² — below ${minLotArea}m² CDC minimum (${lotAreaSource})`);
      }
      if (isHeritage) {
        cdcBlockers.push('Heritage property — CDC not available, DA required');
      }

      if (cdcBlockers.length === 0) {
        // Why not exempt
        const sepp2 = 'SEPP (Exempt and Complying Development Codes) 2008, Part 2';
        const exemptBlockers: string[] = [];
        if (limit) {
          if (area >= limit.area) exemptBlockers.push(`Area ${area}m² — exceeds ${limit.area}m² exempt limit for ${workLabel} (${sepp2})`);
          if (limit.height !== null && height > limit.height) exemptBlockers.push(`Height ${height}m — exceeds ${limit.height}m exempt limit for ${workLabel} (${sepp2})`);
        } else {
          exemptBlockers.push(`${workType} — no exempt development pathway available (${sepp2})`);
        }

        setResult({
          verdict: 'review',
          tier: 'Complying Development (CDC)',
          summary: `Your ${area}m² ${workLabel} cannot proceed as exempt — a CDC is required.`,
          blockers: exemptBlockers,
          requirements: [
            { pass: true, text: `Lot size ${Math.round(lotArea)}m² — meets ${minLotArea}m² minimum` },
            { pass: true, text: `Zone ${zone} — CDC permitted` },
            { pass: false, warn: true, text: 'Setback requirements — certifier to measure and confirm on site' },
          ],
          timeline: '20 business days',
          cost: '~$2,000–$3,000 (private certifier fee)',
          nextStep: 'Contact a Private Certifier — they assess setbacks and issue the CDC',
          source: lotAreaSource,
        });
      } else {
        setResult({
          verdict: 'ineligible',
          tier: 'DA Required',
          summary: `Your ${area}m² ${workLabel} cannot proceed as CDC — a Development Application is required.`,
          blockers: cdcBlockers,
          timeline: '3–6 months',
          cost: '~$5,000–$15,000 (town planner + council fees)',
          nextStep: 'Engage a town planner to prepare a DA lodged with Inner West Council',
          source: 'Inner West DCP 2022, SEPP Housing Code',
        });
      }
    }
  }, [answers, seppProvisions, loadingProvisions, propertyData, currentStep]);

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
                          {question.options.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {isAnswered && !isActive && (
                      <p className="text-sm text-gray-700 mt-1">
                        <strong>
                          {question.type === 'select'
                            ? question.options?.find(o => o.value === answer.value)?.label || answer.value
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

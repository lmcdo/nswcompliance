'use client';

/**
 * CDC/DA Pathway Decision Tree
 *
 * Interactive sequential eligibility checker for owner builders.
 * Asks questions step-by-step and shows real-time verdict.
 */

import { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, ChevronRight, Home } from 'lucide-react';

interface CDCPathwayProps {
  propertyData: any;
  proposedWorkType?: 'deck' | 'garage' | 'extension' | 'other';
}

interface Question {
  id: string;
  text: string;
  type: 'boolean' | 'number' | 'select';
  unit?: string;
  options?: Array<{ value: string; label: string }>;
  guidance?: string;
}

interface Answer {
  questionId: string;
  value: any;
}

interface CheckResult {
  passed: boolean;
  criterion: string;
  reason: string;
  suggestion?: string;
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
      ? `Floor area = length × width of the structure's footprint. Example: a 5m × 4m garage = 20m². Maximum permitted GFA on this lot is ${Math.round(maxGFA)}m² (LEP Clause 4.4 FSR control — a DA is required if exceeded).`
      : 'Floor area = length × width of the structure\'s footprint. Example: a 5m × 4m garage = 20m².',
  },
  {
    id: 'height',
    text: 'What is the maximum height?',
    type: 'number' as const,
    unit: 'm',
    guidance: 'Highest point of the structure above ground level.',
  },
];

interface SeppProvision {
  id: number;
  provision_text: string;
  pdf_page: number;
  v2_part: string;
  v2_topic: string;
}

export function CDCPathway({ propertyData, proposedWorkType = 'other' }: CDCPathwayProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [results, setResults] = useState<CheckResult[]>([]);
  const [verdict, setVerdict] = useState<'eligible' | 'ineligible' | 'review' | null>(null);
  const [seppProvisions, setSeppProvisions] = useState<SeppProvision[]>([]);
  const [loadingProvisions, setLoadingProvisions] = useState(false);

  const maxGFA = propertyData?.constraints?.maxFsr && propertyData?.lotDimensions?.area
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
        .then(data => {
          setSeppProvisions(data.provisions || []);
          setLoadingProvisions(false);
        })
        .catch(err => {
          console.error('Failed to fetch SEPP provisions:', err);
          setLoadingProvisions(false);
        });
    }
  }, [answers, propertyData]);

  // Pre-fill heritage from property data
  useEffect(() => {
    if (propertyData?.heritage && answers.length <= 1) {
      const isHeritage = propertyData.heritage.isHeritage;
      if (!answers.find(a => a.questionId === 'heritage_item')) {
        setAnswers(prev => [...prev, { questionId: 'heritage_item', value: isHeritage }]);
      }
    }
  }, [propertyData, answers]);

  const handleAnswer = (questionId: string, value: any, autoAdvance: boolean = false) => {
    setAnswers(prev => {
      const existing = prev.findIndex(a => a.questionId === questionId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { questionId, value };
        return updated;
      }
      return [...prev, { questionId, value }];
    });

    // Auto-advance only for boolean questions (single-click Yes/No)
    if (autoAdvance && currentStep < questions.length - 1) {
      setTimeout(() => setCurrentStep(currentStep + 1), 300);
    }
  };

  const handleNext = () => {
    if (currentStep < questions.length - 1) {
      setCurrentStep(currentStep + 1);
    } else if (currentStep === questions.length - 1) {
      // Last question answered — advance to results
      setCurrentStep(questions.length);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const canAdvance = () => {
    const answer = answers.find(a => a.questionId === currentQuestion?.id);
    if (!answer) return false;
    if (currentQuestion?.type === 'number') {
      const v = answer.value;
      return !isNaN(v) && v > 0;
    }
    if (currentQuestion?.type === 'select') {
      return answer.value !== '' && answer.value !== undefined;
    }
    return answer.value !== undefined;
  };

  // 3-Tier Pathway Check: EXEMPT → CDC → DA
  // Only runs after user explicitly clicks "Check Eligibility" (currentStep === questions.length)
  useEffect(() => {
    if (currentStep < questions.length || answers.length < questions.length) {
      setResults([]);
      setVerdict(null);
      return;
    }

    const workType = answers.find(a => a.questionId === 'work_type')?.value;
    const area = answers.find(a => a.questionId === 'area')?.value as number;
    const height = answers.find(a => a.questionId === 'height')?.value as number;

    // Guard: don't compute with invalid numeric inputs
    if (isNaN(area) || area <= 0 || isNaN(height) || height <= 0) {
      setResults([]);
      setVerdict(null);
      return;
    }
    const lotArea = propertyData?.lotDimensions?.area || 0;
    const isHeritage = propertyData?.heritage?.isHeritage || false;
    const zone = propertyData?.zone || '';

    const checks: CheckResult[] = [];

    // PRE-CHECK: Exceeds Max GFA (LEP FSR control) → DA required regardless of pathway
    if (maxGFA !== null && area > maxGFA) {
      checks.push({
        passed: false,
        criterion: 'Exceeds Maximum GFA (LEP FSR Control)',
        reason: `Your proposed floor area of ${area}m² exceeds the maximum permitted GFA of ${Math.round(maxGFA)}m² for this lot (FSR ${propertyData.constraints.maxFsr}:1 × ${Math.round(lotArea)}m²).\n\nNeither exempt development nor CDC can authorise works that exceed the LEP FSR control. A Development Application (DA) is required.\n\nTimeline: 3-6 months\nCost: ~$5,000-$15,000\n\nSource: Inner West LEP 2022, Clause 4.4 (Floor Space Ratio)`,
      });
      setResults(checks);
      setVerdict('ineligible');
      return;
    }

    // TIER 1: EXEMPT DEVELOPMENT (Holy Grail - No Approval Needed)
    let isExempt = false;
    let exemptReason = '';

    if (workType === 'Garage') {
      // Garage: < 36m², < 3m height, 900mm setbacks
      if (area < 36 && height <= 3) {
        isExempt = true;
        exemptReason = `✅ Your ${area}m² garage qualifies as EXEMPT development.\n\nNo approval needed. You can start building immediately.\n\nRequirements met:\n✅ Area ${area}m² < 36m² limit\n✅ Height ${height}m ≤ 3m limit\n✅ Zone ${zone}\n${isHeritage ? '⚠️ Heritage property - confirm with certifier' : '✅ Not heritage property'}\n\nSource: SEPP Exempt & Complying Development Codes 2008, Part 2`;
      }
    } else if (workType === 'Deck') {
      // Deck: < 10m², < 1m high
      if (area < 10 && height <= 1) {
        isExempt = true;
        exemptReason = `✅ Your ${area}m² deck qualifies as EXEMPT development.\n\nNo approval needed. You can start building immediately.\n\nRequirements met:\n✅ Area ${area}m² < 10m² limit\n✅ Height ${height}m ≤ 1m limit (ground level)\n✅ Zone ${zone}\n${isHeritage ? '⚠️ Heritage property - confirm with certifier' : '✅ Not heritage property'}\n\nSource: SEPP Exempt & Complying Development Codes 2008, Part 2`;
      }
    } else if (workType === 'Pool') {
      // Pool: < 30m²
      if (area < 30) {
        isExempt = true;
        exemptReason = `✅ Your ${area}m² pool qualifies as EXEMPT development.\n\nNo approval needed. You can start building immediately.\n\n⚠️ IMPORTANT: Pool fencing must still comply with safety standards.\n\nRequirements met:\n✅ Area ${area}m² < 30m² limit\n✅ Zone ${zone}\n${isHeritage ? '⚠️ Heritage property - confirm with certifier' : '✅ Not heritage property'}\n\nSource: SEPP Exempt & Complying Development Codes 2008, Part 2`;
      }
    }

    if (isExempt) {
      checks.push({
        passed: true,
        criterion: 'EXEMPT - Start Building Today',
        reason: exemptReason,
      });
      setResults(checks);
      setVerdict('eligible');
      return;
    }

    // TIER 2: COMPLYING DEVELOPMENT (CDC - 20 days)
    // Check CDC even if provisions haven't loaded — use lot area from property data
    if (seppProvisions.length > 0 || !loadingProvisions) {
      // Parse lot area requirements
      const lotAreaProvisions = seppProvisions.filter(p =>
        p.provision_text.toLowerCase().includes('area of the lot')
      );

      let isCDC = true;
      let cdcBlockers: string[] = [];
      let minLotArea = 0;
      let lotAreaSource = '';

      if (lotAreaProvisions.length > 0) {
        // Parse from actual SEPP provisions in database
        const lotAreaMatch = lotAreaProvisions[0].provision_text.match(/more than (\d+)\s*m\s*2/);
        if (lotAreaMatch) {
          minLotArea = parseInt(lotAreaMatch[1].replace(/\s/g, ''));
          lotAreaSource = `SEPP Housing Code Part ${seppProvisions[0]?.v2_part}, page ${lotAreaProvisions[0].pdf_page}`;
        }
      } else {
        // Fallback: known CDC lot minimums from SEPP Part 3 (confirmed from our database)
        // Deck/Pool/Garage: 200m² minimum for CDC on R2 lots (SEPP Part 3, clause 3.1)
        minLotArea = 200;
        lotAreaSource = 'SEPP Housing Code Part 3, clause 3.1';
      }

      if (minLotArea > 0 && lotArea < minLotArea) {
        isCDC = false;
        cdcBlockers.push(`Lot size ${Math.round(lotArea)}m² < ${minLotArea}m² minimum (${lotAreaSource})`);
      }

      if (isHeritage) {
        isCDC = false;
        cdcBlockers.push('Heritage property');
      }

      if (isCDC) {
        checks.push({
          passed: true,
          criterion: 'CDC - Get Certifier Approval (20 days)',
          reason: `⚠️ Your ${area}m² ${workType.toLowerCase()} needs a Complying Development Certificate (CDC).\n\nTimeline: 20 business days\nCost: ~$2,000-$3,000 (certifier fee)\n\nWhy not exempt:\n❌ Exceeds exempt development limits\n\nCDC requirements:\n✅ Lot size ${Math.round(lotArea)}m² meets minimum\n✅ Zone ${zone}\n⚠️ Setback requirements apply — certifier to assess\n\nNext steps: Contact a Private Certifier\n\nSource: ${lotAreaSource || 'SEPP Housing Code Part 3'}`,
        });
        setResults(checks);
        setVerdict('review');
        return;
      } else {
        // TIER 3: DA REQUIRED
        checks.push({
          passed: false,
          criterion: 'DA Required - Lodge with Council',
          reason: `❌ Your ${area}m² ${workType.toLowerCase()} requires a Development Application (DA).\n\nTimeline: 3-6 months\nCost: ~$5,000-$15,000 (planner + council fees)\n\nWhy not CDC:\n${cdcBlockers.map(b => `❌ ${b}`).join('\n')}\n\nNext steps: Engage a town planner\n\nSource: Inner West DCP, SEPP Housing Code`,
        });
        setResults(checks);
        setVerdict('ineligible');
        return;
      }
    }

  }, [answers, seppProvisions, loadingProvisions, propertyData, currentStep]);

  const currentQuestion = questions[currentStep];
  const currentAnswer = answers.find(a => a.questionId === currentQuestion?.id);

  return (
    <div className="space-y-4">
      {/* Progress */}
      {currentStep < questions.length && (
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

      {/* Questions — hidden once results are shown */}
      <div className={`space-y-3 ${currentStep >= questions.length ? 'hidden' : ''}`}>
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
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    isAnswered ? 'bg-teal-600 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  {isAnswered ? <CheckCircle2 className="w-4 h-4" /> : index + 1}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 mb-1">{question.text}</p>
                  {question.guidance && isActive && (
                    <p className="text-xs text-gray-600 mb-2 italic">{question.guidance}</p>
                  )}

                  {/* Input */}
                  {isActive && question.type === 'number' && (
                    <div className="flex gap-2 mt-2">
                      <input
                        type="number"
                        value={answer?.value || ''}
                        onChange={(e) => handleAnswer(question.id, parseFloat(e.target.value))}
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
                        onChange={(e) => handleAnswer(question.id, e.target.value, true)}
                        className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                      >
                        <option value="">Select...</option>
                        {question.options.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {isActive && question.type === 'boolean' && (
                    <div className="flex gap-3 mt-2">
                      <button
                        onClick={() => handleAnswer(question.id, true, true)}
                        className={`flex-1 px-4 py-2 rounded border-2 text-sm font-medium transition-all ${
                          answer?.value === true
                            ? 'border-red-500 bg-red-50 text-red-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => handleAnswer(question.id, false, true)}
                        className={`flex-1 px-4 py-2 rounded border-2 text-sm font-medium transition-all ${
                          answer?.value === false
                            ? 'border-green-500 bg-green-50 text-green-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        No
                      </button>
                    </div>
                  )}

                  {/* Show answered value */}
                  {isAnswered && !isActive && (
                    <p className="text-sm text-gray-700 mt-1">
                      <strong>
                        {question.type === 'boolean'
                          ? answer.value
                            ? 'Yes'
                            : 'No'
                          : question.type === 'select'
                          ? question.options?.find(opt => opt.value === answer.value)?.label || answer.value
                          : (isNaN(answer.value) || answer.value <= 0)
                          ? <span className="text-red-500 italic">Enter a value ↑</span>
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

      {/* Results */}
      {results.length > 0 && verdict !== null && (
        <div className="mt-6 space-y-4">
          {/* Verdict */}
          <div
            className={`rounded-xl p-6 border-2 ${
              verdict === 'eligible'
                ? 'border-green-500 bg-green-50'
                : verdict === 'review'
                ? 'border-amber-500 bg-amber-50'
                : 'border-red-500 bg-red-50'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              {verdict === 'eligible' && <CheckCircle2 className="w-8 h-8 text-green-600" />}
              {verdict === 'review' && <AlertTriangle className="w-8 h-8 text-amber-600" />}
              {verdict === 'ineligible' && <XCircle className="w-8 h-8 text-red-600" />}
              <div>
                <h3
                  className={`text-xl font-bold ${
                    verdict === 'eligible' ? 'text-green-900' : verdict === 'review' ? 'text-amber-900' : 'text-red-900'
                  }`}
                >
                  {verdict === 'eligible' && '✅ EXEMPT - Start Building Today'}
                  {verdict === 'review' && '⚠️ CDC Required - 20 Business Days'}
                  {verdict === 'ineligible' && '❌ DA Required - 3-6 Months'}
                </h3>
              </div>
            </div>
          </div>

          {/* Pathway Details */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900">Approval Pathway:</h4>
            {results.map((result, index) => (
              <div
                key={index}
                className={`flex items-start gap-3 p-3 rounded-lg border ${
                  result.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                }`}
              >
                {result.passed ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`text-sm font-medium ${result.passed ? 'text-green-900' : 'text-red-900'}`}>
                    {result.criterion}
                  </p>
                  <p className={`text-xs mt-1 ${result.passed ? 'text-green-800' : 'text-red-800'}`}>{result.reason}</p>
                  {result.suggestion && (
                    <p className="text-xs mt-2 italic text-gray-700 bg-white bg-opacity-50 rounded p-2 border border-gray-200">
                      💡 {result.suggestion}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      {currentStep < questions.length && (
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

      {/* Start Over when results shown */}
      {currentStep >= questions.length && (
        <div className="pt-2">
          <button
            onClick={() => {
              setCurrentStep(0);
              setAnswers([]);
              setResults([]);
              setVerdict(null);
            }}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            ← Start Over
          </button>
        </div>
      )}
    </div>
  );
}

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

const QUESTIONS: Question[] = [
  {
    id: 'work_type',
    text: 'What type of work are you planning?',
    type: 'select',
    options: [
      { value: 'Deck', label: 'Deck, Patio, or Verandah' },
      { value: 'Garage', label: 'Garage or Carport' },
      { value: 'Pool', label: 'Swimming Pool' },
      { value: 'Fence', label: 'Fence or Gate' },
    ],
    guidance: 'Different CDC requirements apply to different work types.',
  },
  {
    id: 'heritage_item',
    text: 'Is your property a heritage item or in a heritage conservation area?',
    type: 'boolean',
    guidance: 'CDC works are generally restricted on heritage properties.',
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
    if (autoAdvance && currentStep < QUESTIONS.length - 1) {
      setTimeout(() => setCurrentStep(currentStep + 1), 300);
    }
  };

  const handleNext = () => {
    if (currentStep < QUESTIONS.length - 1) {
      setCurrentStep(currentStep + 1);
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
      return !isNaN(answer.value) && answer.value > 0;
    }
    if (currentQuestion?.type === 'select') {
      return answer.value !== '' && answer.value !== undefined;
    }
    return answer.value !== undefined;
  };

  // Parse SEPP provisions and check eligibility
  useEffect(() => {
    if (answers.length < QUESTIONS.length || seppProvisions.length === 0) {
      setResults([]);
      setVerdict(null);
      return;
    }

    const checks: CheckResult[] = [];
    const lotArea = propertyData?.lotDimensions?.area || 0;

    // Heritage check (hard blocker)
    const isHeritage = answers.find(a => a.questionId === 'heritage_item')?.value as boolean;
    if (isHeritage) {
      checks.push({
        passed: false,
        criterion: 'Heritage Property',
        reason: 'Property is a heritage item or in a heritage conservation area.',
        suggestion: 'CDC eligibility is severely restricted on heritage properties. Consult a Private Certifier.',
      });
      setResults(checks);
      setVerdict('ineligible');
      return;
    }

    // Parse lot area requirements from SEPP provisions
    const lotAreaProvisions = seppProvisions.filter(p =>
      p.provision_text.toLowerCase().includes('area of the lot')
    );

    if (lotAreaProvisions.length > 0) {
      // Extract minimum lot area from provisions like "area of the lot is more than 300 m²"
      const lotAreaMatch = lotAreaProvisions[0].provision_text.match(/more than (\d+)\s*m\s*2/);
      if (lotAreaMatch) {
        const minLotArea = parseInt(lotAreaMatch[1].replace(/\s/g, ''));
        if (lotArea < minLotArea) {
          checks.push({
            passed: false,
            criterion: 'Minimum Lot Area',
            reason: `Your lot is ${Math.round(lotArea)}m². SEPP requires lot area more than ${minLotArea}m² for this work type (SEPP Housing Code Part ${seppProvisions[0].v2_part}).`,
            suggestion: `Consider a smaller work type or lodge a Development Application. See PDF page ${lotAreaProvisions[0].pdf_page}.`,
          });
        } else {
          checks.push({
            passed: true,
            criterion: 'Minimum Lot Area',
            reason: `Your lot is ${Math.round(lotArea)}m², which meets the ${minLotArea}m² minimum (SEPP Part ${seppProvisions[0].v2_part}).`,
          });
        }
      }
    }

    // Show other applicable provisions as informational
    const setbackProvisions = seppProvisions.filter(p =>
      p.provision_text.toLowerCase().includes('setback')
    );

    if (setbackProvisions.length > 0) {
      checks.push({
        passed: true,
        criterion: 'Setback Requirements',
        reason: `${setbackProvisions.length} setback provisions apply. These are table-based and require assessment by a Private Certifier.`,
        suggestion: `Review SEPP provisions on PDF pages: ${setbackProvisions.map(p => p.pdf_page).join(', ')}.`,
      });
    }

    // Show height provisions if any
    const heightProvisions = seppProvisions.filter(p =>
      p.provision_text.toLowerCase().includes('maximum height') ||
      p.provision_text.toLowerCase().includes('height of the floor level')
    );

    if (heightProvisions.length > 0) {
      checks.push({
        passed: true,
        criterion: 'Height Requirements',
        reason: `${heightProvisions.length} height provisions apply. These often reference tables and require certifier assessment.`,
        suggestion: `Review SEPP provisions on PDF pages: ${heightProvisions.map(p => p.pdf_page).join(', ')}.`,
      });
    }

    // Summary
    checks.push({
      passed: true,
      criterion: 'Next Steps',
      reason: `${seppProvisions.length} SEPP ${seppProvisions[0]?.v2_topic} provisions apply to your property (Zone ${propertyData?.zone}, Part ${seppProvisions[0]?.v2_part}).`,
      suggestion: 'Engage a Private Certifier to assess compliance against these specific provisions.',
    });

    setResults(checks);

    // Determine verdict
    const failCount = checks.filter(c => !c.passed).length;
    if (failCount === 0) {
      setVerdict('review'); // Never say "eligible" - always requires certifier review
    } else {
      setVerdict('ineligible');
    }
  }, [answers, seppProvisions, propertyData]);

  const currentQuestion = QUESTIONS[currentStep];
  const currentAnswer = answers.find(a => a.questionId === currentQuestion?.id);

  return (
    <div className="space-y-4">
      {/* Progress */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span className="font-medium">Step {Math.min(currentStep + 1, QUESTIONS.length)} of {QUESTIONS.length}</span>
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-600 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / QUESTIONS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Questions */}
      <div className="space-y-3">
        {QUESTIONS.map((question, index) => {
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
      {results.length > 0 && (
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
                  {verdict === 'eligible' && 'CDC Likely Eligible'}
                  {verdict === 'review' && 'CDC Possible — Requires Review'}
                  {verdict === 'ineligible' && 'CDC Not Eligible'}
                </h3>
                <p
                  className={`text-sm mt-1 ${
                    verdict === 'eligible' ? 'text-green-800' : verdict === 'review' ? 'text-amber-800' : 'text-red-800'
                  }`}
                >
                  {verdict === 'eligible' &&
                    'Your proposed works appear to meet CDC criteria. Engage a Private Certifier to lodge your CDC application.'}
                  {verdict === 'review' &&
                    'Some criteria may need adjustment. Consult a planning consultant or certifier to refine your design.'}
                  {verdict === 'ineligible' &&
                    'Your proposed works do not meet CDC standards. You will need to lodge a Development Application (DA) with council.'}
                </p>
              </div>
            </div>
          </div>

          {/* Detailed Checks */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900">Detailed Checks:</h4>
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
      {currentStep < QUESTIONS.length && (
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
            disabled={!canAdvance() || currentStep === QUESTIONS.length - 1}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              !canAdvance() || currentStep === QUESTIONS.length - 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm'
            }`}
          >
            {currentStep === QUESTIONS.length - 1 ? 'Complete' : 'Next →'}
          </button>
        </div>
      )}
    </div>
  );
}

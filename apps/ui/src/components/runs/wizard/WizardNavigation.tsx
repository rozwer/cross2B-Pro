"use client";

interface WizardNavigationProps {
  currentStep: number;
  totalSteps: number;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  canSubmit: boolean;
}

export function WizardNavigation({
  currentStep,
  totalSteps,
  onBack,
  onNext,
  onSubmit,
  isSubmitting,
  canSubmit,
}: WizardNavigationProps) {
  const isFirstStep = currentStep === 1;
  const isLastStep = currentStep === totalSteps;

  return (
    <div className="mt-6 flex justify-between">
      {/* Back Button */}
      <button
        type="button"
        onClick={onBack}
        disabled={isFirstStep}
        className={`
          inline-flex items-center px-4 py-2 text-sm font-medium rounded-md
          ${
            isFirstStep
              ? "text-gray-400 cursor-not-allowed"
              : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
          }
        `}
      >
        <svg
          className="mr-2 h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        戻る
      </button>

      {/* Next/Submit Button */}
      {isLastStep ? (
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting || !canSubmit}
          className={`
            inline-flex items-center px-6 py-2 text-sm font-medium rounded-md text-white
            ${
              isSubmitting || !canSubmit
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-primary-600 hover:bg-primary-700"
            }
          `}
        >
          {isSubmitting ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              作成中...
            </>
          ) : (
            <>
              記事生成を開始
              <svg
                className="ml-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </>
          )}
        </button>
      ) : (
        <button
          type="button"
          onClick={onNext}
          className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
        >
          次へ
          <svg
            className="ml-2 h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

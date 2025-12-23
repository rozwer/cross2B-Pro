"use client";

interface Step {
  id: number;
  label: string;
  description: string;
}

interface WizardProgressProps {
  steps: Step[];
  currentStep: number;
}

export function WizardProgress({ steps, currentStep }: WizardProgressProps) {
  return (
    <nav aria-label="Progress">
      <ol className="flex items-center">
        {steps.map((step, stepIdx) => (
          <li
            key={step.id}
            className={`relative ${stepIdx !== steps.length - 1 ? "flex-1" : ""}`}
          >
            <div className="flex items-center">
              {/* Step Circle */}
              <div
                className={`
                  relative flex h-10 w-10 items-center justify-center rounded-full
                  ${
                    step.id < currentStep
                      ? "bg-primary-600 text-white"
                      : step.id === currentStep
                      ? "border-2 border-primary-600 bg-white text-primary-600"
                      : "border-2 border-gray-300 bg-white text-gray-500"
                  }
                `}
              >
                {step.id < currentStep ? (
                  <svg
                    className="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  <span className="text-sm font-medium">{step.id}</span>
                )}
              </div>

              {/* Step Label (visible on larger screens) */}
              <div className="ml-3 hidden sm:block">
                <p
                  className={`text-sm font-medium ${
                    step.id <= currentStep ? "text-primary-600" : "text-gray-500"
                  }`}
                >
                  {step.label}
                </p>
              </div>

              {/* Connector Line */}
              {stepIdx !== steps.length - 1 && (
                <div
                  className={`
                    ml-4 mr-4 h-0.5 flex-1
                    ${step.id < currentStep ? "bg-primary-600" : "bg-gray-300"}
                  `}
                />
              )}
            </div>
          </li>
        ))}
      </ol>
    </nav>
  );
}

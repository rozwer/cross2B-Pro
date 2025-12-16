'use client';

import { CheckCircle, XCircle, Clock, Loader2, Pause } from 'lucide-react';
import type { Step, StepStatus } from '@/lib/types';
import { STEP_LABELS } from '@/lib/types';
import { cn } from '@/lib/utils';
import { StepNode } from './StepNode';

interface StepTimelineProps {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
  onRetry?: (stepName: string) => void;
  onResume?: (stepName: string) => void;
}

export function StepTimeline({
  steps,
  currentStep,
  waitingApproval,
  onRetry,
  onResume,
}: StepTimelineProps) {
  const stepMap = new Map(steps.map((s) => [s.step_name, s]));

  // STEP_NAMESの順序でstepsを表示
  const orderedSteps = Object.keys(STEP_LABELS).map((stepName) => {
    const step = stepMap.get(stepName);
    return {
      name: stepName,
      label: STEP_LABELS[stepName],
      step,
    };
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Step Timeline</h3>
      <div className="space-y-1">
        {orderedSteps.map((item, index) => (
          <StepNode
            key={item.name}
            stepName={item.name}
            label={item.label}
            step={item.step}
            isCurrent={item.name === currentStep}
            isWaitingApproval={waitingApproval && item.name === currentStep}
            isLast={index === orderedSteps.length - 1}
            onRetry={onRetry}
            onResume={onResume}
          />
        ))}
      </div>
    </div>
  );
}

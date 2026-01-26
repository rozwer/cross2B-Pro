"use client";

import { RefreshCw, ArrowLeft, Info } from "lucide-react";
import { RetryRecommendation, getStepLabel } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RetryRecommendationBannerProps {
  recommendation: RetryRecommendation;
  onRetry?: (step: string) => void;
  onResume?: (step: string) => void;
  className?: string;
}

/**
 * リトライ推奨バナーコンポーネント
 *
 * ステップ失敗時に表示され、エラーカテゴリに基づいて
 * 適切なリトライ方法を推奨する。
 *
 * 表示条件:
 * - run.status === "failed"
 * - run.retry_recommendation が存在
 * - run.needs_github_fix === false
 */
export function RetryRecommendationBanner({
  recommendation,
  onRetry,
  onResume,
  className,
}: RetryRecommendationBannerProps) {
  const { action, target_step, reason } = recommendation;
  const targetStepLabel = getStepLabel(target_step);

  const handleClick = () => {
    if (action === "retry_same") {
      onRetry?.(target_step);
    } else {
      onResume?.(target_step);
    }
  };

  const isRetrySame = action === "retry_same";
  const Icon = isRetrySame ? RefreshCw : ArrowLeft;
  const buttonText = isRetrySame
    ? `${targetStepLabel} を再実行`
    : `${targetStepLabel} から再開`;

  return (
    <div
      className={cn(
        "bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-4",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Info className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
            リトライ推奨
          </h3>
          <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
            {reason}
          </p>
          <div className="mt-3">
            <button
              onClick={handleClick}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
                isRetrySame
                  ? "bg-red-500 hover:bg-red-600 text-white"
                  : "bg-violet-500 hover:bg-violet-600 text-white"
              )}
            >
              <Icon className="h-4 w-4" />
              {buttonText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

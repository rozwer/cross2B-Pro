"use client";

import { Clock, AlertTriangle, CheckCircle, FileText, Activity } from "lucide-react";
import type { Step, StepAttempt, ValidationReport } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface StepDetailPanelProps {
  step: Step;
}

export function StepDetailPanel({ step }: StepDetailPanelProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {step.step_name} 詳細
        </h3>
      </div>

      <div className="p-4 space-y-4">
        {/* タイミング情報 */}
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          <Clock className="h-4 w-4" />
          <span>
            {step.started_at ? formatDate(step.started_at) : "未開始"}
            {step.completed_at && ` → ${formatDate(step.completed_at)}`}
          </span>
        </div>

        {/* エラー情報 */}
        {step.status === "failed" && step.error_message && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
            <h4 className="text-xs font-medium text-red-700 dark:text-red-300 mb-2 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              エラー情報
            </h4>
            {step.error_code && (
              <div className="mb-2">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                    step.error_code === "RETRYABLE"
                      ? "bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200"
                      : step.error_code === "NON_RETRYABLE"
                        ? "bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-200"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                  )}
                >
                  {step.error_code === "RETRYABLE"
                    ? "再試行可能"
                    : step.error_code === "NON_RETRYABLE"
                      ? "再試行不可"
                      : step.error_code}
                </span>
              </div>
            )}
            <p className="text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap break-words">
              {step.error_message}
            </p>
          </div>
        )}

        {/* 試行履歴 */}
        <div>
          <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
            <Activity className="h-3.5 w-3.5" />
            試行履歴
          </h4>
          <div className="space-y-2">
            {step.attempts.map((attempt, index) => (
              <AttemptCard key={attempt.id} attempt={attempt} index={index} />
            ))}
            {step.attempts.length === 0 && (
              <p className="text-xs text-gray-400 dark:text-gray-500">試行なし</p>
            )}
          </div>
        </div>

        {/* バリデーションレポート */}
        {step.validation_report && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              バリデーション
            </h4>
            <ValidationReportSummary report={step.validation_report} />
          </div>
        )}
      </div>
    </div>
  );
}

function AttemptCard({ attempt, index }: { attempt: StepAttempt; index: number }) {
  return (
    <div
      className={cn(
        "p-2 rounded border text-xs",
        attempt.status === "succeeded" &&
          "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800",
        attempt.status === "failed" &&
          "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800",
        attempt.status === "running" &&
          "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-gray-900 dark:text-gray-100">
          試行 #{attempt.attempt_num}
        </span>
        <span
          className={cn(
            "px-1.5 py-0.5 rounded text-xs",
            attempt.status === "succeeded" &&
              "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300",
            attempt.status === "failed" &&
              "bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300",
            attempt.status === "running" &&
              "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300",
          )}
        >
          {attempt.status}
        </span>
      </div>
      <div className="text-gray-500 dark:text-gray-400 mt-1">
        {formatDate(attempt.started_at)}
        {attempt.completed_at && ` → ${formatDate(attempt.completed_at)}`}
      </div>
      {attempt.error && (
        <div className="mt-1 text-red-600 dark:text-red-400">
          [{attempt.error.type}] {attempt.error.message}
        </div>
      )}
      {attempt.repairs && attempt.repairs.length > 0 && (
        <div className="mt-1 text-amber-600 dark:text-amber-400">
          修正適用: {attempt.repairs.map((r) => r.repair_type).join(", ")}
        </div>
      )}
    </div>
  );
}

function ValidationReportSummary({ report }: { report: ValidationReport }) {
  return (
    <div
      className={cn(
        "p-2 rounded border text-xs",
        report.valid
          ? "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800"
          : "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800",
      )}
    >
      <div className="flex items-center gap-2">
        {report.valid ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-red-500" />
        )}
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {report.valid ? "検証OK" : "検証NG"}
        </span>
        <span className="text-gray-500 dark:text-gray-400">({report.format})</span>
      </div>
      {report.errors.length > 0 && (
        <ul className="mt-2 space-y-1">
          {report.errors.slice(0, 3).map((err, i) => (
            <li key={i} className="text-red-600 dark:text-red-400">
              {err.path && `[${err.path}] `}
              {err.message}
            </li>
          ))}
          {report.errors.length > 3 && (
            <li className="text-gray-500 dark:text-gray-400">
              ...他 {report.errors.length - 3} 件
            </li>
          )}
        </ul>
      )}
      {report.warnings.length > 0 && (
        <ul className="mt-2 space-y-1">
          {report.warnings.slice(0, 3).map((warn, i) => (
            <li key={i} className="text-amber-600 dark:text-amber-400">
              {warn.path && `[${warn.path}] `}
              {warn.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

"use client";

import { ExternalLink, CheckCircle2, AlertCircle, X } from "lucide-react";

export interface ReviewIssue {
  severity: "high" | "medium" | "low";
  category: string;
  location: string;
  original: string;
  issue: string;
  suggestion: string;
}

export interface ReviewResult {
  review_type: string;
  issues: ReviewIssue[];
  summary: {
    total_issues: number;
    high: number;
    medium: number;
    low: number;
    overall_assessment: string;
  };
  passed: boolean;
}

export interface ReviewStatus {
  status: "pending" | "in_progress" | "completed" | "failed";
  issue_number: number | null;
  issue_url: string | null;
  has_result: boolean;
  result_path: string | null;
}

type ReviewType = "fact_check" | "seo" | "quality" | "all";

const reviewTypeLabels: Record<ReviewType, string> = {
  all: "総合レビュー",
  fact_check: "ファクトチェック",
  seo: "SEO最適化",
  quality: "文章品質",
};

function getSeverityColor(severity: string): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800 border-red-200";
    case "medium":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "low":
      return "bg-blue-100 text-blue-800 border-blue-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

interface ReviewResultPanelProps {
  reviewResult: ReviewResult;
  reviewStatus: ReviewStatus | null;
  onClose: () => void;
  onEditWithClaude?: (issue: ReviewIssue) => void;
}

export function ReviewResultPanel({
  reviewResult,
  reviewStatus,
  onClose,
  onEditWithClaude,
}: ReviewResultPanelProps) {
  return (
    <div className="w-1/3 border-l border-gray-200 bg-gray-50 overflow-y-auto h-[calc(100vh-180px)] mt-4">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">レビュー結果</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* サマリー */}
        <div
          className={`p-4 rounded-lg mb-4 ${
            reviewResult.passed ? "bg-green-50" : "bg-amber-50"
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            {reviewResult.passed ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-600" />
            )}
            <span
              className={`font-medium ${
                reviewResult.passed ? "text-green-800" : "text-amber-800"
              }`}
            >
              {reviewTypeLabels[reviewResult.review_type as ReviewType] ||
                reviewResult.review_type}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            {reviewResult.summary.overall_assessment}
          </p>
          <div className="flex gap-4 text-sm">
            <span className="text-red-600">
              🔴 高: {reviewResult.summary.high}
            </span>
            <span className="text-yellow-600">
              🟡 中: {reviewResult.summary.medium}
            </span>
            <span className="text-blue-600">
              🟢 低: {reviewResult.summary.low}
            </span>
          </div>
        </div>

        {/* 問題リスト */}
        {reviewResult.issues.length > 0 ? (
          <div className="space-y-3">
            {reviewResult.issues.map((issue, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${getSeverityColor(
                  issue.severity
                )}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium uppercase">
                      {issue.severity}
                    </span>
                    <span className="text-xs text-gray-500">
                      {issue.category}
                    </span>
                  </div>
                  {onEditWithClaude && (
                    <button
                      onClick={() => onEditWithClaude(issue)}
                      className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
                    >
                      編集
                    </button>
                  )}
                </div>
                <p className="text-sm font-medium text-gray-900 mb-1">
                  {issue.location}
                </p>
                <p className="text-sm text-gray-600 mb-2">{issue.issue}</p>
                {issue.suggestion && (
                  <div className="text-sm bg-white/50 p-2 rounded">
                    <span className="font-medium">修正案: </span>
                    {issue.suggestion}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 text-center py-4">
            問題は検出されませんでした
          </p>
        )}

        {/* GitHub Issue リンク */}
        {reviewStatus?.issue_url && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <a
              href={reviewStatus.issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-purple-600 hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              GitHub Issue #{reviewStatus.issue_number} を開く
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

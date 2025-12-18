"use client";

import {
  X,
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  Pause,
  ChevronRight,
  FileText,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";
import type { Step, StepAttempt } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useState } from "react";

/**
 * Step Detail Drawer
 * - Shows internal sub-steps/phases for each workflow step
 * - Displays attempt history, logs, artifacts
 * - Allows retry actions
 */

interface StepDetailDrawerProps {
  step: Step | null;
  stepName?: string; // Allow showing drawer even without full step data
  onClose: () => void;
  onRetry?: (stepName: string) => void;
  isOpen: boolean;
}

// Mock sub-steps for each main step (in real app, this comes from API)
const SUB_STEPS: Record<string, Array<{ id: string; name: string; description: string }>> = {
  "step-1": [
    { id: "input-validate", name: "入力検証", description: "キーワードと要件の形式チェック" },
    { id: "input-normalize", name: "データ正規化", description: "入力データの標準化" },
  ],
  step0: [
    { id: "prep-config", name: "設定読み込み", description: "モデル設定とパラメータの初期化" },
    { id: "prep-context", name: "コンテキスト準備", description: "実行環境の準備" },
  ],
  step1: [
    { id: "analysis-keyword", name: "キーワード解析", description: "検索意図と関連語の分析" },
    { id: "analysis-serp", name: "SERP分析", description: "検索結果ページの構造分析" },
    { id: "analysis-intent", name: "検索意図分類", description: "ユーザーインテントの特定" },
  ],
  step2: [
    { id: "research-fetch", name: "ページ取得", description: "競合ページのコンテンツ取得" },
    { id: "research-extract", name: "コンテンツ抽出", description: "本文とメタデータの抽出" },
    { id: "research-analyze", name: "競合分析", description: "競合の強み・弱みの分析" },
  ],
  step3: [
    { id: "outline-generate", name: "構成生成", description: "AI による記事構成の生成" },
    { id: "outline-validate", name: "構成検証", description: "構成の論理性チェック" },
  ],
  step3a: [
    { id: "content-a-gen", name: "コンテンツ生成", description: "セクションAの本文生成" },
    { id: "content-a-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  step3b: [
    { id: "content-b-gen", name: "コンテンツ生成", description: "セクションBの本文生成" },
    { id: "content-b-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  step3c: [
    { id: "content-c-gen", name: "コンテンツ生成", description: "セクションCの本文生成" },
    { id: "content-c-validate", name: "品質チェック", description: "生成内容の品質検証" },
  ],
  step4: [
    { id: "prep-merge", name: "コンテンツ統合", description: "並列生成結果の統合" },
    { id: "prep-order", name: "構成最適化", description: "セクション順序の最適化" },
  ],
  step5: [
    { id: "write-intro", name: "導入部生成", description: "リード文と導入セクション" },
    { id: "write-body", name: "本文生成", description: "メインコンテンツの生成" },
    { id: "write-conclusion", name: "結論生成", description: "まとめセクションの生成" },
  ],
  step6: [
    { id: "edit-grammar", name: "文法チェック", description: "文法・表現の修正" },
    { id: "edit-style", name: "スタイル調整", description: "トーン・文体の統一" },
    { id: "edit-seo", name: "SEO最適化", description: "キーワード密度の調整" },
  ],
  "step6.5": [
    { id: "package-bundle", name: "バンドル作成", description: "成果物のパッケージング" },
    { id: "package-validate", name: "整合性検証", description: "パッケージの検証" },
  ],
  step7a: [
    { id: "html-generate", name: "HTML生成", description: "マークアップの生成" },
    { id: "html-validate", name: "HTML検証", description: "構文とアクセシビリティ検証" },
  ],
  step7b: [
    { id: "meta-title", name: "タイトル生成", description: "SEOタイトルの生成" },
    { id: "meta-description", name: "メタ説明生成", description: "メタディスクリプションの生成" },
    { id: "meta-og", name: "OGP生成", description: "ソーシャルメタタグの生成" },
  ],
  step8: [
    { id: "verify-seo", name: "SEO検証", description: "SEOスコアのチェック" },
    { id: "verify-quality", name: "品質検証", description: "コンテンツ品質の最終確認" },
    { id: "verify-links", name: "リンク検証", description: "内部・外部リンクの検証" },
  ],
  step9: [{ id: "adjust-final", name: "最終調整", description: "検証結果に基づく修正" }],
  step10: [
    { id: "complete-save", name: "保存処理", description: "成果物の最終保存" },
    { id: "complete-notify", name: "完了通知", description: "完了ステータスの更新" },
  ],
};

export function StepDetailDrawer({
  step,
  stepName: propStepName,
  onClose,
  onRetry,
  isOpen,
}: StepDetailDrawerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Use stepName from prop if step is not available
  const effectiveStepName = step?.step_name || propStepName;

  // Don't render if drawer is not open or no step info at all
  if (!isOpen || !effectiveStepName) return null;

  const subSteps = SUB_STEPS[effectiveStepName] || [];
  const attempts = step?.attempts || [];
  const lastAttempt = attempts[attempts.length - 1];
  const status = step?.status;

  // Calculate sub-step progress based on step status
  const getSubStepStatus = (index: number) => {
    if (!status) return "pending";
    if (status === "completed") return "completed";
    if (status === "failed") {
      // Assume failed at last sub-step
      return index < subSteps.length - 1 ? "completed" : "failed";
    }
    if (status === "running") {
      // Simulate progress through sub-steps
      const progress = Math.floor((Date.now() / 1000) % subSteps.length);
      if (index < progress) return "completed";
      if (index === progress) return "running";
      return "pending";
    }
    return "pending";
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case "running":
        return <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={cn(
          "fixed right-0 top-0 bottom-0 w-full max-w-md bg-white dark:bg-gray-900 shadow-2xl z-50",
          "transform transition-transform duration-300 ease-out",
          "border-l border-gray-200 dark:border-gray-700",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center",
                status === "completed" && "bg-emerald-100 dark:bg-emerald-900/30",
                status === "running" && "bg-cyan-100 dark:bg-cyan-900/30",
                status === "failed" && "bg-red-100 dark:bg-red-900/30",
                (!status || status === "pending") && "bg-gray-100 dark:bg-gray-800",
              )}
            >
              {status === "completed" && (
                <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              )}
              {status === "running" && (
                <Loader2 className="w-5 h-5 text-cyan-600 dark:text-cyan-400 animate-spin" />
              )}
              {status === "failed" && (
                <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              )}
              {(!status || status === "pending") && <Clock className="w-5 h-5 text-gray-500" />}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {STEP_LABELS[effectiveStepName] || effectiveStepName}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                {effectiveStepName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-80px)]">
          {/* Sub-steps Progress */}
          <div className="p-6 border-b border-gray-100 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <ChevronRight className="w-4 h-4" />
              内部ステップ
            </h3>
            <div className="space-y-3">
              {subSteps.map((subStep, index) => {
                const status = getSubStepStatus(index);
                return (
                  <div
                    key={subStep.id}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-lg transition-colors",
                      status === "completed" && "bg-emerald-50 dark:bg-emerald-900/20",
                      status === "running" && "bg-cyan-50 dark:bg-cyan-900/20",
                      status === "failed" && "bg-red-50 dark:bg-red-900/20",
                      status === "pending" && "bg-gray-50 dark:bg-gray-800/50 opacity-60",
                    )}
                  >
                    <div className="flex-shrink-0 mt-0.5">{getStatusIcon(status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            status === "completed" && "text-emerald-700 dark:text-emerald-400",
                            status === "running" && "text-cyan-700 dark:text-cyan-400",
                            status === "failed" && "text-red-700 dark:text-red-400",
                            status === "pending" && "text-gray-500 dark:text-gray-400",
                          )}
                        >
                          {subStep.name}
                        </span>
                        {status === "running" && (
                          <span className="text-xs text-cyan-600 dark:text-cyan-400">
                            処理中...
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {subStep.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Attempt History */}
          {attempts.length > 0 && (
            <div className="p-6 border-b border-gray-100 dark:border-gray-800">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                試行履歴
                <span className="ml-auto text-xs font-normal text-gray-500">
                  {attempts.length}回
                </span>
              </h3>
              <div className="space-y-2">
                {attempts.map((attempt, index) => (
                  <div
                    key={attempt.id}
                    className={cn(
                      "p-3 rounded-lg border",
                      attempt.status === "succeeded" &&
                        "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800",
                      attempt.status === "failed" &&
                        "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
                      attempt.status === "running" &&
                        "bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800",
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        試行 #{attempt.attempt_num}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(attempt.started_at).toLocaleTimeString()}
                      </span>
                    </div>
                    {attempt.error && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                        {attempt.error.message}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Artifacts */}
          {step?.artifacts && step.artifacts.length > 0 && (
            <div className="p-6 border-b border-gray-100 dark:border-gray-800">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                生成物
              </h3>
              <div className="space-y-2">
                {step.artifacts.map((artifact) => (
                  <div
                    key={artifact.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 font-mono truncate max-w-[200px]">
                          {artifact.ref_path.split("/").pop()}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(artifact.size_bytes / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => copyToClipboard(artifact.ref_path, artifact.id)}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        title="パスをコピー"
                      >
                        {copiedId === artifact.id ? (
                          <Check className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      <button
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        title="開く"
                      >
                        <ExternalLink className="w-4 h-4 text-gray-400" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timing Info */}
          {step && (step.started_at || step.completed_at) && (
            <div className="p-6">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
                タイミング
              </h3>
              <div className="space-y-2 text-sm">
                {step.started_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">開始</span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {new Date(step.started_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {step.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">完了</span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {new Date(step.completed_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {step.started_at && step.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">所要時間</span>
                    <span className="text-gray-700 dark:text-gray-300">
                      {(
                        (new Date(step.completed_at).getTime() -
                          new Date(step.started_at).getTime()) /
                        1000
                      ).toFixed(1)}
                      秒
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {status === "failed" && onRetry && (
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => onRetry(effectiveStepName)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              このステップをリトライ
            </button>
          </div>
        )}
      </div>
    </>
  );
}

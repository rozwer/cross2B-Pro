"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  X,
  RefreshCw,
  Check,
  FileText,
  Code,
  File,
  ChevronDown,
  ChevronRight,
  Eye,
  Package,
  Loader2,
  MessageSquare,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/utils";
import type { ArtifactRef, ArtifactContent, Step3ReviewItem, Step3StepName } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { api } from "@/lib/api";
import { JsonViewer } from "@/components/artifacts/JsonViewer";
import { MarkdownViewer } from "@/components/artifacts/MarkdownViewer";
import { StepContentViewer } from "@/components/artifacts/StepContentViewer";
import { Loading } from "@/components/common/Loading";

// 承認対象のステップ（並列処理ステップ）
const STEP3_STEPS: Step3StepName[] = ["step3a", "step3b", "step3c"];

interface Step3ReviewDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  runId: string;
}

interface StepReviewState {
  step: Step3StepName;
  decision: "approve" | "retry" | null;
  instruction: string;
  retryCount: number;
}

export function Step3ReviewDialog({
  isOpen,
  onClose,
  onComplete,
  runId,
}: Step3ReviewDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 成果物関連
  const [artifacts, setArtifacts] = useState<ArtifactRef[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set(STEP3_STEPS));

  // 各ステップのレビュー状態
  const [stepReviews, setStepReviews] = useState<StepReviewState[]>(
    STEP3_STEPS.map((step) => ({
      step,
      decision: null,
      instruction: "",
      retryCount: 0,
    }))
  );

  // 成果物のフェッチ
  useEffect(() => {
    if (isOpen) {
      setArtifactsLoading(true);
      api.artifacts.list(runId)
        .then((data) => {
          setArtifacts(data);
        })
        .catch((err) => {
          console.error("Failed to fetch artifacts:", err);
        })
        .finally(() => {
          setArtifactsLoading(false);
        });
    }
  }, [isOpen, runId]);

  // Step3成果物のフィルタリング
  const step3Artifacts = useMemo(() => {
    return artifacts.filter((a) => STEP3_STEPS.includes(a.step_name as Step3StepName));
  }, [artifacts]);

  // ステップごとにグループ化
  const groupedArtifacts = useMemo(() => {
    const groups = step3Artifacts.reduce(
      (acc, artifact) => {
        const stepKey = artifact.step_name;
        if (!acc[stepKey]) {
          acc[stepKey] = [];
        }
        acc[stepKey].push(artifact);
        return acc;
      },
      {} as Record<string, ArtifactRef[]>
    );

    return STEP3_STEPS.filter((step) => groups[step]).map((step) => [step, groups[step]] as const);
  }, [step3Artifacts]);

  // コンテンツ読み込み
  const loadContent = useCallback(async (artifact: ArtifactRef) => {
    setSelectedArtifact(artifact);
    setContentLoading(true);
    try {
      const data = await api.artifacts.download(runId, artifact.id);
      setContent(data);
    } catch (err) {
      console.error("Failed to load artifact content:", err);
      setContent(null);
    } finally {
      setContentLoading(false);
    }
  }, [runId]);

  // ダイアログ表示制御
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
      document.body.style.overflow = "hidden";
    } else {
      dialog.close();
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // 最初の成果物を自動選択
  useEffect(() => {
    if (isOpen && step3Artifacts.length > 0 && !selectedArtifact) {
      loadContent(step3Artifacts[0]);
    }
  }, [isOpen, step3Artifacts, selectedArtifact, loadContent]);

  // キャンセルイベント
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [onClose]);

  // ダイアログを閉じる時に状態をリセット
  useEffect(() => {
    if (!isOpen) {
      setSelectedArtifact(null);
      setContent(null);
      setArtifacts([]);
      setSubmitError(null);
      setStepReviews(
        STEP3_STEPS.map((step) => ({
          step,
          decision: null,
          instruction: "",
          retryCount: 0,
        }))
      );
    }
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  const toggleStep = (stepKey: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepKey)) {
      newExpanded.delete(stepKey);
    } else {
      newExpanded.add(stepKey);
    }
    setExpandedSteps(newExpanded);
  };

  // レビュー状態の更新
  const updateStepReview = (step: Step3StepName, updates: Partial<StepReviewState>) => {
    setStepReviews((prev) =>
      prev.map((r) => (r.step === step ? { ...r, ...updates } : r))
    );
  };

  // 全ステップ承認
  const approveAll = () => {
    setStepReviews((prev) =>
      prev.map((r) => ({ ...r, decision: "approve" as const, instruction: "" }))
    );
  };

  // 送信可能かチェック
  const canSubmit = useMemo(() => {
    // 全てのステップに決定が必要
    const allDecided = stepReviews.every((r) => r.decision !== null);
    // リトライのステップには指示が推奨（空でも許可）
    return allDecided;
  }, [stepReviews]);

  // 送信
  const handleSubmit = async () => {
    if (!canSubmit) return;

    setLoading(true);
    setSubmitError(null);

    try {
      const reviews: Step3ReviewItem[] = stepReviews.map((r) => ({
        step: r.step,
        accepted: r.decision === "approve",
        retry: r.decision === "retry",
        retry_instruction: r.decision === "retry" ? r.instruction : "",
      }));

      await api.runs.step3Review(runId, reviews);
      onComplete();
    } catch (err) {
      console.error("Step3 review failed:", err);
      setSubmitError(err instanceof Error ? err.message : "レビューの送信に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (contentType: string) => {
    if (contentType.includes("json")) return <Code className="h-4 w-4 text-amber-600" />;
    if (contentType.includes("html")) return <FileText className="h-4 w-4 text-orange-600" />;
    if (contentType.includes("markdown")) return <FileText className="h-4 w-4 text-blue-600" />;
    return <File className="h-4 w-4 text-gray-500" />;
  };

  const getStepReview = (step: Step3StepName) => {
    return stepReviews.find((r) => r.step === step);
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-0 flex items-center justify-center p-4 bg-black/30">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-in">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/40 rounded-lg">
                <MessageSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Step3 レビュー
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  各ステップの成果物を確認し、承認またはリトライを選択してください
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={approveAll}
                disabled={loading}
                className="px-3 py-1.5 text-sm text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/50 transition-colors"
              >
                全て承認
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                aria-label="閉じる"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 flex overflow-hidden min-h-0">
            {artifactsLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 p-8">
                <Loader2 className="h-12 w-12 text-primary-500 animate-spin mb-4" />
                <p className="text-lg font-medium">成果物を読み込み中...</p>
              </div>
            ) : step3Artifacts.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 p-8">
                <Package className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
                <p className="text-lg font-medium">Step3の成果物がありません</p>
                <p className="text-sm text-gray-400 mt-1">
                  step3a, step3b, step3c の成果物が生成されると表示されます
                </p>
              </div>
            ) : (
              <>
                {/* Artifacts List + Review Panel (Left) */}
                <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 overflow-y-auto bg-gray-50 dark:bg-gray-900/50 flex flex-col">
                  <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 sticky top-0 z-10">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                      <Package className="h-4 w-4" />
                      <span>Step3 成果物</span>
                      <span className="ml-auto px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded text-xs">
                        {step3Artifacts.length}
                      </span>
                    </div>
                  </div>

                  {groupedArtifacts.map(([stepKey, stepArtifacts]) => {
                    const review = getStepReview(stepKey);
                    return (
                      <div key={stepKey} className="border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                        {/* Step Header */}
                        <button
                          onClick={() => toggleStep(stepKey)}
                          className="w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-white dark:hover:bg-gray-800 transition-colors"
                        >
                          {expandedSteps.has(stepKey) ? (
                            <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          )}
                          <div className="flex-1 text-left">
                            <span className="font-medium text-gray-900 dark:text-gray-100">
                              {STEP_LABELS[stepKey] || stepKey}
                            </span>
                          </div>
                          {review?.decision === "approve" && (
                            <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded text-xs">
                              承認
                            </span>
                          )}
                          {review?.decision === "retry" && (
                            <span className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 rounded text-xs">
                              リトライ
                            </span>
                          )}
                          {!review?.decision && (
                            <span className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">
                              未選択
                            </span>
                          )}
                        </button>

                        {expandedSteps.has(stepKey) && (
                          <div className="bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
                            {/* Files */}
                            {stepArtifacts.map((artifact) => (
                              <button
                                key={artifact.id}
                                onClick={() => loadContent(artifact)}
                                className={cn(
                                  "w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors border-l-2",
                                  selectedArtifact?.id === artifact.id
                                    ? "bg-primary-50 dark:bg-primary-900/30 border-primary-500"
                                    : "hover:bg-gray-50 dark:hover:bg-gray-700/50 border-transparent"
                                )}
                              >
                                {getIcon(artifact.content_type)}
                                <div className="flex-1 min-w-0 text-left">
                                  <p className="truncate text-gray-900 dark:text-gray-100 text-xs font-medium">
                                    {artifact.ref_path.split("/").pop() || "output"}
                                  </p>
                                  <p className="text-xs text-gray-400">
                                    {formatBytes(artifact.size_bytes)}
                                  </p>
                                </div>
                                <Eye className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                              </button>
                            ))}

                            {/* Review Controls */}
                            <div className="p-3 border-t border-gray-100 dark:border-gray-700 space-y-2">
                              <div className="flex gap-2">
                                <button
                                  onClick={() => updateStepReview(stepKey, { decision: "approve", instruction: "" })}
                                  disabled={loading}
                                  className={cn(
                                    "flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs rounded-md transition-colors",
                                    review?.decision === "approve"
                                      ? "bg-green-500 text-white"
                                      : "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700 hover:bg-green-100 dark:hover:bg-green-900/50"
                                  )}
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  承認
                                </button>
                                <button
                                  onClick={() => updateStepReview(stepKey, { decision: "retry" })}
                                  disabled={loading}
                                  className={cn(
                                    "flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs rounded-md transition-colors",
                                    review?.decision === "retry"
                                      ? "bg-amber-500 text-white"
                                      : "bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-700 hover:bg-amber-100 dark:hover:bg-amber-900/50"
                                  )}
                                >
                                  <RefreshCw className="h-3.5 w-3.5" />
                                  リトライ
                                </button>
                              </div>

                              {/* Retry Instruction */}
                              {review?.decision === "retry" && (
                                <textarea
                                  value={review.instruction}
                                  onChange={(e) => updateStepReview(stepKey, { instruction: e.target.value })}
                                  placeholder="修正指示を入力してください..."
                                  className="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                                  rows={2}
                                />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Content Viewer (Right Panel) */}
                <div className="flex-1 flex flex-col overflow-hidden">
                  {contentLoading ? (
                    <div className="flex-1 flex items-center justify-center">
                      <Loading text="読み込み中..." />
                    </div>
                  ) : selectedArtifact && content ? (
                    <>
                      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          {getIcon(selectedArtifact.content_type)}
                          <span className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                            {selectedArtifact.ref_path.split("/").pop()}
                          </span>
                          <span className="text-xs text-gray-400 px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">
                            {STEP_LABELS[selectedArtifact.step_name] || selectedArtifact.step_name}
                          </span>
                        </div>
                      </div>
                      <div className="flex-1 overflow-auto p-4">
                        <ContentRenderer
                          content={content.content}
                          contentType={selectedArtifact.content_type}
                          encoding={content.encoding}
                          stepName={selectedArtifact.step_name}
                          fileName={selectedArtifact.ref_path.split("/").pop() || "output.json"}
                        />
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
                      <Eye className="h-12 w-12 mb-3 text-gray-300 dark:text-gray-600" />
                      <p className="text-sm">ファイルを選択してプレビュー</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            {submitError && (
              <div className="mb-3 flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg text-sm text-red-700 dark:text-red-300">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {submitError}
              </div>
            )}
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {stepReviews.filter((r) => r.decision !== null).length} / {STEP3_STEPS.length} ステップ確認済み
              </div>
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  disabled={loading}
                  className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={loading || !canSubmit}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      送信中...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      レビュー送信
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </dialog>
  );
}

// Markdownコンテンツを含むフィールド名
const MARKDOWN_FIELDS = [
  "draft",
  "polished",
  "final_content",
  "integration_package",
  "markdown",
  "content",
  "article",
  "body",
];

function ContentRenderer({
  content,
  contentType,
  encoding,
  stepName,
  fileName,
}: {
  content: string;
  contentType: string;
  encoding: "utf-8" | "base64";
  stepName: string;
  fileName: string;
}) {
  const [viewMode, setViewMode] = useState<"formatted" | "json" | "markdown">("formatted");
  const decodedContent = encoding === "base64" ? atob(content) : content;

  if (contentType.includes("json")) {
    let markdownContent: string | null = null;
    let markdownFieldName: string | null = null;
    let isValidJson = false;

    try {
      const parsed = JSON.parse(decodedContent);
      isValidJson = true;
      if (typeof parsed === "object" && parsed !== null) {
        for (const field of MARKDOWN_FIELDS) {
          if (field in parsed && typeof parsed[field] === "string" && parsed[field].length > 100) {
            markdownContent = parsed[field];
            markdownFieldName = field;
            break;
          }
        }
      }
    } catch {
      // JSONパースエラー
    }

    if (isValidJson && fileName === "output.json" && stepName) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                <Code className="h-3 w-3 inline-block mr-1" />
                JSON
              </button>
              <button
                onClick={() => setViewMode("formatted")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "formatted"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                <FileText className="h-3 w-3 inline-block mr-1" />
                整形表示
              </button>
              {markdownContent && markdownFieldName && (
                <button
                  onClick={() => setViewMode("markdown")}
                  className={cn(
                    "px-3 py-1 text-xs font-medium rounded transition-colors",
                    viewMode === "markdown"
                      ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  )}
                >
                  <FileText className="h-3 w-3 inline-block mr-1" />
                  {markdownFieldName}
                </button>
              )}
            </div>
          </div>
          {viewMode === "json" ? (
            <JsonViewer content={decodedContent} />
          ) : viewMode === "formatted" ? (
            <StepContentViewer content={decodedContent} stepName={stepName} />
          ) : markdownContent ? (
            <MarkdownViewer content={markdownContent} />
          ) : null}
        </div>
      );
    }

    if (markdownContent && markdownFieldName) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                <Code className="h-3 w-3 inline-block mr-1" />
                JSON
              </button>
              <button
                onClick={() => setViewMode("markdown")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "markdown"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                <FileText className="h-3 w-3 inline-block mr-1" />
                {markdownFieldName}
              </button>
            </div>
          </div>
          {viewMode === "json" ? (
            <JsonViewer content={decodedContent} />
          ) : (
            <MarkdownViewer content={markdownContent} />
          )}
        </div>
      );
    }

    return <JsonViewer content={decodedContent} />;
  }

  if (contentType.includes("markdown")) {
    return <MarkdownViewer content={decodedContent} />;
  }

  return (
    <pre className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs text-gray-900 dark:text-gray-100 overflow-auto max-h-[400px] whitespace-pre-wrap font-mono border border-gray-200 dark:border-gray-700">
      {decodedContent}
    </pre>
  );
}

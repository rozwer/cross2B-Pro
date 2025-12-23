"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import {
  X,
  AlertTriangle,
  Check,
  FileText,
  Code,
  ImageIcon,
  File,
  ChevronDown,
  ChevronRight,
  Eye,
  Package,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/utils";
import type { ArtifactRef, ArtifactContent } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { api } from "@/lib/api";
import { JsonViewer } from "@/components/artifacts/JsonViewer";
import { MarkdownViewer } from "@/components/artifacts/MarkdownViewer";
import { HtmlPreview } from "@/components/artifacts/HtmlPreview";
import { StepContentViewer } from "@/components/artifacts/StepContentViewer";
import { Loading } from "@/components/common/Loading";

// 承認対象のステップ（並列処理ステップ）
const APPROVAL_TARGET_STEPS = ["step3a", "step3b", "step3c"];

interface ApprovalDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
  runId: string;
  artifacts: ArtifactRef[];
  loading?: boolean;
}

export function ApprovalDialog({
  isOpen,
  onClose,
  onApprove,
  onReject,
  runId,
  artifacts,
  loading = false,
}: ApprovalDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [rejectMode, setRejectMode] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set(APPROVAL_TARGET_STEPS));

  // 承認対象ステップの成果物のみフィルタリング
  const approvalArtifacts = useMemo(() => {
    return artifacts.filter((a) => APPROVAL_TARGET_STEPS.includes(a.step_name));
  }, [artifacts]);

  // ステップごとにグループ化
  const groupedArtifacts = useMemo(() => {
    const groups = approvalArtifacts.reduce(
      (acc, artifact) => {
        const stepKey = artifact.step_name;
        if (!acc[stepKey]) {
          acc[stepKey] = [];
        }
        acc[stepKey].push(artifact);
        return acc;
      },
      {} as Record<string, ArtifactRef[]>,
    );

    // ステップ順序でソート
    return APPROVAL_TARGET_STEPS.filter((step) => groups[step]).map((step) => [step, groups[step]] as const);
  }, [approvalArtifacts]);

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
    if (isOpen && approvalArtifacts.length > 0 && !selectedArtifact) {
      loadContent(approvalArtifacts[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, approvalArtifacts.length]);

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
      setRejectMode(false);
      setRejectReason("");
      setSelectedArtifact(null);
      setContent(null);
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

  const loadContent = async (artifact: ArtifactRef) => {
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
  };

  const getIcon = (contentType: string) => {
    if (contentType.includes("json")) return <Code className="h-4 w-4 text-amber-600" />;
    if (contentType.includes("html")) return <FileText className="h-4 w-4 text-orange-600" />;
    if (contentType.includes("markdown")) return <FileText className="h-4 w-4 text-blue-600" />;
    if (contentType.includes("image")) return <ImageIcon className="h-4 w-4 text-green-600" />;
    return <File className="h-4 w-4 text-gray-500" />;
  };

  const handleReject = () => {
    onReject(rejectReason || "Rejected by user");
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-0 flex items-center justify-center p-4 bg-black/30">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col overflow-hidden animate-scale-in">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-yellow-50 to-orange-50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">承認確認</h2>
                <p className="text-sm text-gray-500">
                  以下の成果物を確認して、承認または却下してください
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="閉じる"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content Area */}
          <div className="flex-1 flex overflow-hidden min-h-0">
            {approvalArtifacts.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 p-8">
                <Package className="h-16 w-16 text-gray-300 mb-4" />
                <p className="text-lg font-medium">承認対象の成果物がありません</p>
                <p className="text-sm text-gray-400 mt-1">
                  step3a, step3b, step3c の成果物が生成されると表示されます
                </p>
              </div>
            ) : (
              <>
                {/* Artifacts List (Left Panel) */}
                <div className="w-64 flex-shrink-0 border-r border-gray-200 overflow-y-auto bg-gray-50">
                  <div className="p-3 border-b border-gray-200 bg-white sticky top-0">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      <Package className="h-4 w-4" />
                      <span>承認対象ファイル</span>
                      <span className="ml-auto px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                        {approvalArtifacts.length}
                      </span>
                    </div>
                  </div>

                  {groupedArtifacts.map(([stepKey, stepArtifacts]) => (
                    <div key={stepKey} className="border-b border-gray-100 last:border-b-0">
                      <button
                        onClick={() => toggleStep(stepKey)}
                        className="w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-white transition-colors"
                      >
                        {expandedSteps.has(stepKey) ? (
                          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        )}
                        <div className="flex-1 text-left">
                          <span className="font-medium text-gray-900">
                            {STEP_LABELS[stepKey] || stepKey}
                          </span>
                        </div>
                        <span className="px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded text-xs">
                          {stepArtifacts.length}
                        </span>
                      </button>

                      {expandedSteps.has(stepKey) && (
                        <div className="bg-white border-t border-gray-100">
                          {stepArtifacts.map((artifact) => (
                            <button
                              key={artifact.id}
                              onClick={() => loadContent(artifact)}
                              className={cn(
                                "w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors border-l-2",
                                selectedArtifact?.id === artifact.id
                                  ? "bg-primary-50 border-primary-500"
                                  : "hover:bg-gray-50 border-transparent",
                              )}
                            >
                              {getIcon(artifact.content_type)}
                              <div className="flex-1 min-w-0 text-left">
                                <p className="truncate text-gray-900 text-xs font-medium">
                                  {artifact.ref_path.split("/").pop() || "output"}
                                </p>
                                <p className="text-xs text-gray-400">
                                  {formatBytes(artifact.size_bytes)}
                                </p>
                              </div>
                              <Eye className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Content Viewer (Right Panel) */}
                <div className="flex-1 flex flex-col overflow-hidden">
                  {contentLoading ? (
                    <div className="flex-1 flex items-center justify-center">
                      <Loading text="読み込み中..." />
                    </div>
                  ) : selectedArtifact && content ? (
                    <>
                      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          {getIcon(selectedArtifact.content_type)}
                          <span className="font-medium text-gray-900 text-sm">
                            {selectedArtifact.ref_path.split("/").pop()}
                          </span>
                          <span className="text-xs text-gray-400 px-2 py-0.5 bg-gray-200 rounded">
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
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                      <Eye className="h-12 w-12 mb-3 text-gray-300" />
                      <p className="text-sm">ファイルを選択してプレビュー</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            {rejectMode ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    却下理由
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="却下理由を入力してください（任意）"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    rows={2}
                    autoFocus
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => {
                      setRejectMode(false);
                      setRejectReason("");
                    }}
                    disabled={loading}
                    className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    戻る
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={loading}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        処理中...
                      </>
                    ) : (
                      <>
                        <X className="h-4 w-4" />
                        却下を確定
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-500">
                  {approvalArtifacts.length > 0
                    ? `${approvalArtifacts.length} 件の成果物を確認してください`
                    : "成果物がありません"}
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    disabled={loading}
                    className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    キャンセル
                  </button>
                  <button
                    onClick={() => setRejectMode(true)}
                    disabled={loading || approvalArtifacts.length === 0}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
                  >
                    <X className="h-4 w-4" />
                    却下
                  </button>
                  <button
                    onClick={onApprove}
                    disabled={loading || approvalArtifacts.length === 0}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        処理中...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4" />
                        承認
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
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
  // デフォルトは整形表示モード
  const [viewMode, setViewMode] = useState<"formatted" | "json" | "markdown">("formatted");
  const decodedContent = encoding === "base64" ? atob(content) : content;

  // JSONの場合
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

    // output.jsonの場合はステップビューアを優先
    if (isValidJson && fileName === "output.json" && stepName) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
            <span className="text-xs text-gray-500 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-600 hover:text-gray-900",
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
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-600 hover:text-gray-900",
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
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900",
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

    // それ以外のJSONファイル
    if (markdownContent && markdownFieldName) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
            <span className="text-xs text-gray-500 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-600 hover:text-gray-900",
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
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-600 hover:text-gray-900",
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

  if (contentType.includes("html")) {
    return <HtmlPreview content={decodedContent} />;
  }

  if (contentType.includes("markdown")) {
    return <MarkdownViewer content={decodedContent} />;
  }

  // Image rendering - display as img tag with data URL
  if (contentType.includes("image")) {
    const dataUrl = `data:${contentType};base64,${content}`;
    return (
      <div className="p-4 flex justify-center">
        <img
          src={dataUrl}
          alt="Generated image"
          className="max-w-full h-auto rounded-lg shadow-sm"
          loading="lazy"
        />
      </div>
    );
  }

  // デフォルト: プレーンテキスト
  return (
    <pre className="p-4 bg-gray-50 rounded-lg text-xs text-gray-900 overflow-auto max-h-[400px] whitespace-pre-wrap font-mono border border-gray-200">
      {decodedContent}
    </pre>
  );
}

"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  FileText,
  Code,
  ImageIcon,
  File,
  Download,
  Upload,
  ChevronDown,
  ChevronRight,
  Eye,
  Package,
  Clock,
  AlertTriangle,
  X,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import type { ArtifactRef, ArtifactContent, GitHubSyncStatus } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { api } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { JsonViewer } from "./JsonViewer";
import { MarkdownViewer } from "./MarkdownViewer";
import { HtmlPreview } from "./HtmlPreview";
import { StepContentViewer } from "./StepContentViewer";
import { GitHubActions } from "./GitHubActions";
import { Loading } from "@/components/common/Loading";

interface ArtifactViewerProps {
  runId: string;
  artifacts: ArtifactRef[];
  // GitHub integration (Phase 4)
  githubRepoUrl?: string;
  githubDirPath?: string;
}

// ステップの順序を定義（アンダースコアとドット表記の両方をサポート）
const STEP_ORDER = [
  "step-1",
  "step0",
  "step1",
  "step1_5",
  "step2",
  "step3",
  "step3a",
  "step3b",
  "step3c",
  "step3_5",
  "step4",
  "step5",
  "step6",
  "step6.5",
  "step6_5",
  "step7",
  "step7a",
  "step7b",
  "step8",
  "step9",
  "step10",
  "step11",
  "step12",
];

// ステップ名から数値部分を抽出してソート用の値を返す
function getStepSortValue(stepName: string): number {
  // step-1 を -1 として扱う
  if (stepName === "step-1") return -1;

  // step{number}{suffix} のパターンを解析
  const match = stepName.match(/^step(\d+)(.*)$/i);
  if (!match) return 999; // マッチしないものは末尾に

  const num = parseInt(match[1], 10);
  const suffix = match[2]?.toLowerCase() || "";

  // サフィックスに基づく小数点を追加
  // 例: step3a -> 3.1, step3b -> 3.2, step6.5 or step6_5 -> 6.5
  if (suffix === ".5" || suffix === "_5") return num + 0.5;
  if (suffix === "a") return num + 0.1;
  if (suffix === "b") return num + 0.2;
  if (suffix === "c") return num + 0.3;

  return num;
}

export function ArtifactViewer({ runId, artifacts, githubRepoUrl, githubDirPath }: ArtifactViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  // GitHub sync status tracking (Phase 5)
  const [syncStatuses, setSyncStatuses] = useState<Record<string, GitHubSyncStatus>>({});

  // Upload dialog state
  const [uploadDialog, setUploadDialog] = useState<{
    isOpen: boolean;
    step: string;
    loading: boolean;
    error: string | null;
    success: string | null;
    invalidateCache: boolean;
  }>({
    isOpen: false,
    step: "",
    loading: false,
    error: null,
    success: null,
    invalidateCache: false,
  });

  // Artifact events/history for selected artifact
  type ArtifactEvent = {
    id: string;
    event_type: string;
    payload: Record<string, unknown>;
    created_at: string;
  };
  const [artifactEvents, setArtifactEvents] = useState<ArtifactEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  // Fetch events for selected artifact's step
  useEffect(() => {
    if (!selectedArtifact) {
      setArtifactEvents([]);
      return;
    }

    const fetchEvents = async () => {
      setEventsLoading(true);
      try {
        const step = selectedArtifact.step_name || selectedArtifact.step_id;
        const events = await api.events.list(runId, { step, limit: 20 });
        // Filter for upload events only
        const uploadEvents = events.filter((e: { event_type: string }) => e.event_type === "upload");
        setArtifactEvents(uploadEvents);
      } catch (err) {
        console.error("Failed to load artifact events:", err);
        setArtifactEvents([]);
      } finally {
        setEventsLoading(false);
      }
    };

    fetchEvents();
  }, [runId, selectedArtifact]);

  // Load sync status when GitHub is configured
  useEffect(() => {
    if (!githubRepoUrl || !githubDirPath) return;

    const loadSyncStatus = async () => {
      try {
        const result = await api.github.getSyncStatus(runId);
        const statusMap: Record<string, GitHubSyncStatus> = {};
        for (const item of result.statuses) {
          statusMap[item.step] = item.status as GitHubSyncStatus;
        }
        setSyncStatuses(statusMap);
      } catch (err) {
        console.error("Failed to load sync status:", err);
      }
    };

    loadSyncStatus();
    // Polling every 30 seconds
    const interval = setInterval(loadSyncStatus, 30000);
    return () => clearInterval(interval);
  }, [runId, githubRepoUrl, githubDirPath]);

  // Callback to update sync status from GitHubActions
  const handleSyncStatusChange = useCallback((step: string, status: GitHubSyncStatus) => {
    setSyncStatuses((prev) => ({ ...prev, [step]: status }));
  }, []);

  // Open upload dialog for a step
  const openUploadDialog = useCallback((step: string) => {
    setUploadDialog({
      isOpen: true,
      step,
      loading: false,
      error: null,
      success: null,
      invalidateCache: false,
    });
  }, []);

  // Handle file upload
  const handleFileUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setUploadDialog((prev) => ({ ...prev, loading: true, error: null, success: null }));

      try {
        const fileContent = await file.text();

        // Validate JSON
        try {
          JSON.parse(fileContent);
        } catch {
          throw new Error("無効なJSONファイルです");
        }

        const result = await api.artifacts.upload(runId, uploadDialog.step, fileContent, {
          invalidateCache: uploadDialog.invalidateCache,
        });

        setUploadDialog((prev) => ({
          ...prev,
          loading: false,
          success: `アップロード完了${result.cache_invalidated ? "（キャッシュ無効化済み）" : ""}`,
        }));

        // Reload selected artifact if it's the same step - trigger a refresh
        if (selectedArtifact?.step_name === uploadDialog.step) {
          // Reload by downloading the content again
          const data = await api.artifacts.download(runId, selectedArtifact.id);
          setContent(data);
        }

        // Close after short delay
        setTimeout(() => {
          setUploadDialog((prev) => ({ ...prev, isOpen: false }));
        }, 2000);
      } catch (error) {
        setUploadDialog((prev) => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error.message : "アップロードに失敗しました",
        }));
      } finally {
        // Reset file input
        event.target.value = "";
      }
    },
    [runId, uploadDialog.step, uploadDialog.invalidateCache, selectedArtifact],
  );

  // step_nameでグループ化し、STEP_ORDERでソート
  const groupedArtifacts = useMemo(() => {
    const groups = artifacts.reduce(
      (acc, artifact) => {
        // step_nameを優先、なければstep_idを使用
        const stepKey = artifact.step_name || artifact.step_id || "unknown";
        if (!acc[stepKey]) {
          acc[stepKey] = [];
        }
        acc[stepKey].push(artifact);
        return acc;
      },
      {} as Record<string, ArtifactRef[]>,
    );

    // ステップ順序でソート（数値ベースでより堅牢なソート）
    const sortedEntries = Object.entries(groups).sort(([a], [b]) => {
      // まずSTEP_ORDERで試す
      const aIndex = STEP_ORDER.indexOf(a);
      const bIndex = STEP_ORDER.indexOf(b);

      if (aIndex !== -1 && bIndex !== -1) {
        return aIndex - bIndex;
      }

      // STEP_ORDERにない場合は数値ベースでソート
      const aVal = getStepSortValue(a);
      const bVal = getStepSortValue(b);

      if (aVal !== bVal) {
        return aVal - bVal;
      }

      // 数値が同じ場合は文字列比較
      return a.localeCompare(b);
    });

    return sortedEntries;
  }, [artifacts]);

  const toggleStep = (stepKey: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepKey)) {
      newExpanded.delete(stepKey);
    } else {
      newExpanded.add(stepKey);
    }
    setExpandedSteps(newExpanded);
  };

  const expandAll = () => {
    setExpandedSteps(new Set(groupedArtifacts.map(([key]) => key)));
  };

  const collapseAll = () => {
    setExpandedSteps(new Set());
  };

  const loadContent = async (artifact: ArtifactRef) => {
    setSelectedArtifact(artifact);
    setLoading(true);
    try {
      const data = await api.artifacts.download(runId, artifact.id);
      setContent(data);
    } catch (err) {
      console.error("Failed to load artifact content:", err);
      setContent(null);
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (contentType: string) => {
    if (contentType.includes("json")) return <Code className="h-4 w-4 text-amber-600 dark:text-amber-400" />;
    if (contentType.includes("html")) return <FileText className="h-4 w-4 text-orange-600 dark:text-orange-400" />;
    if (contentType.includes("markdown")) return <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />;
    if (contentType.includes("image")) return <ImageIcon className="h-4 w-4 text-green-600 dark:text-green-400" />;
    return <File className="h-4 w-4 text-gray-500 dark:text-gray-400" />;
  };

  const getStepLabel = (stepKey: string) => {
    return STEP_LABELS[stepKey] || stepKey;
  };

  // 成果物の総数とサイズを計算
  const totalSize = artifacts.reduce((sum, a) => sum + (a.size_bytes || 0), 0);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* ヘッダー */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Package className="h-5 w-5 text-primary-600 dark:text-primary-400" />
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">成果物</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {artifacts.length} ファイル · {formatBytes(totalSize)}
              </p>
            </div>
          </div>
          {artifacts.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={expandAll}
                className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                すべて展開
              </button>
              <button
                onClick={collapseAll}
                className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                すべて折りたたむ
              </button>
            </div>
          )}
        </div>
      </div>

      {artifacts.length === 0 ? (
        <div className="p-8 text-center">
          <Package className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">成果物がありません</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            ワークフローが進行すると成果物が表示されます
          </p>
        </div>
      ) : (
        <div className="flex divide-x divide-gray-200 dark:divide-gray-700" style={{ minHeight: "400px" }}>
          {/* ファイルリスト（左パネル） */}
          <div className="w-72 flex-shrink-0 overflow-y-auto max-h-[600px]">
            {groupedArtifacts.map(([stepKey, stepArtifacts]) => (
              <div key={stepKey} className="border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                <div className="flex items-center">
                  <button
                    onClick={() => toggleStep(stepKey)}
                    className="flex-1 flex items-center gap-2 px-4 py-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    {expandedSteps.has(stepKey) ? (
                      <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    )}
                    <div className="flex-1 text-left min-w-0">
                      <div className="font-medium text-gray-900 dark:text-gray-100 truncate flex items-center gap-1.5">
                        {getStepLabel(stepKey)}
                        {/* GitHub sync status badge (Phase 5) */}
                        {githubRepoUrl && syncStatuses[stepKey] === "diverged" && (
                          <span title="GitHub と差分あり">
                            <AlertTriangle className="h-3.5 w-3.5 text-orange-500 flex-shrink-0" />
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {stepKey} · {stepArtifacts.length} ファイル
                      </div>
                    </div>
                    <span className="flex-shrink-0 px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                      {stepArtifacts.length}
                    </span>
                  </button>
                  {/* Upload button for step */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openUploadDialog(stepKey);
                    }}
                    className="p-2 mr-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-colors"
                    title={`${getStepLabel(stepKey)} にアップロード`}
                  >
                    <Upload className="h-4 w-4" />
                  </button>
                </div>

                {expandedSteps.has(stepKey) && (
                  <div className="bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700">
                    {stepArtifacts.map((artifact) => (
                      <button
                        key={artifact.id}
                        onClick={() => loadContent(artifact)}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                          selectedArtifact?.id === artifact.id
                            ? "bg-primary-50 dark:bg-primary-900/30 border-l-2 border-primary-500"
                            : "hover:bg-gray-100 dark:hover:bg-gray-700/50 border-l-2 border-transparent",
                        )}
                      >
                        {getIcon(artifact.content_type)}
                        <div className="flex-1 min-w-0 text-left">
                          <p className="truncate text-gray-900 dark:text-gray-100 text-xs font-medium">
                            {artifact.ref_path.split("/").pop() || "output"}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                            <span>{formatBytes(artifact.size_bytes)}</span>
                            <span className="text-gray-300 dark:text-gray-600">·</span>
                            <span className="truncate">{artifact.content_type.split("/").pop()}</span>
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

          {/* コンテンツビューア（右パネル） */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {loading ? (
              <div className="flex-1 flex items-center justify-center">
                <Loading text="読み込み中..." />
              </div>
            ) : selectedArtifact && content ? (
              <>
                {/* ファイル情報ヘッダー */}
                <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      {getIcon(selectedArtifact.content_type)}
                      <div className="min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {selectedArtifact.ref_path.split("/").pop()}
                        </h4>
                        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                          <span className="flex items-center gap-1">
                            <Package className="h-3 w-3" />
                            {formatBytes(selectedArtifact.size_bytes)}
                          </span>
                          <span>{selectedArtifact.content_type}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(selectedArtifact.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        // Handle UTF-8 content properly for download
                        const blob = content.encoding === "base64"
                          ? new Blob([Uint8Array.from(atob(content.content), c => c.charCodeAt(0))], { type: selectedArtifact.content_type })
                          : new Blob([content.content], { type: selectedArtifact.content_type });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = selectedArtifact.ref_path.split("/").pop() || "download";
                        a.click();
                        URL.revokeObjectURL(url);
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" />
                      ダウンロード
                    </button>
                  </div>
                  {/* GitHub Actions (Phase 4) */}
                  {githubRepoUrl && githubDirPath && (
                    <div className="mt-2">
                      <GitHubActions
                        runId={runId}
                        step={selectedArtifact.step_name || selectedArtifact.step_id}
                        githubRepoUrl={githubRepoUrl}
                        githubDirPath={githubDirPath}
                        initialSyncStatus={syncStatuses[selectedArtifact.step_name || selectedArtifact.step_id]}
                        onSyncStatusChange={handleSyncStatusChange}
                      />
                    </div>
                  )}
                  {/* Upload History */}
                  {artifactEvents.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        編集履歴
                      </h5>
                      <div className="space-y-1.5 max-h-24 overflow-y-auto">
                        {artifactEvents.map((event) => (
                          <div
                            key={event.id}
                            className="text-xs text-gray-600 dark:text-gray-400 flex items-center gap-2"
                          >
                            <span className="inline-flex items-center px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                              <Upload className="h-2.5 w-2.5 mr-1" />
                              upload
                            </span>
                            <span className="text-gray-400 dark:text-gray-500">
                              {formatDate(event.created_at)}
                            </span>
                            <span className="truncate">
                              {String(event.payload.user_id || "unknown")}
                            </span>
                            {(() => {
                              const details = event.payload.details as Record<string, unknown> | undefined;
                              return details?.cache_invalidated ? (
                                <span className="text-orange-500 dark:text-orange-400" title="キャッシュ無効化">
                                  🔄
                                </span>
                              ) : null;
                            })()}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {eventsLoading && (
                    <div className="mt-2 text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      履歴を読み込み中...
                    </div>
                  )}
                </div>

                {/* コンテンツエリア */}
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
                <p className="text-xs mt-1">左のリストからファイルをクリックしてください</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload Dialog */}
      {uploadDialog.isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                成果物をアップロード
              </h2>
              <button
                onClick={() => setUploadDialog((prev) => ({ ...prev, isOpen: false }))}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium">{getStepLabel(uploadDialog.step)}</span> ({uploadDialog.step}) の成果物を置き換えます。
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                既存のファイルはバックアップされます。
              </p>
            </div>

            <div className="mb-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={uploadDialog.invalidateCache}
                  onChange={(e) =>
                    setUploadDialog((prev) => ({ ...prev, invalidateCache: e.target.checked }))
                  }
                  className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900"
                />
                <span className="text-gray-700 dark:text-gray-300">次回実行時に再生成する（キャッシュ無効化）</span>
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1 ml-6">
                チェックすると、このステップを再実行した際に新たに生成されます
              </p>
            </div>

            {/* Error Message */}
            {uploadDialog.error && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-md">
                <p className="text-sm text-red-600 dark:text-red-400">{uploadDialog.error}</p>
              </div>
            )}

            {/* Success Message */}
            {uploadDialog.success && (
              <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-md flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                <p className="text-sm text-green-600 dark:text-green-400">{uploadDialog.success}</p>
              </div>
            )}

            <label className="block">
              <span className="sr-only">ファイルを選択</span>
              <input
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                disabled={uploadDialog.loading}
                className="block w-full text-sm text-gray-500 dark:text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 dark:file:bg-blue-900/30 file:text-blue-700 dark:file:text-blue-300
                  hover:file:bg-blue-100 dark:hover:file:bg-blue-900/50
                  disabled:opacity-50"
              />
            </label>

            {uploadDialog.loading && (
              <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                アップロード中...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
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
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
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
                    ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
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
                      ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
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
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">表示モード:</span>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-md p-0.5">
              <button
                onClick={() => setViewMode("json")}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded transition-colors",
                  viewMode === "json"
                    ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
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
                    ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
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
    <pre className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs text-gray-900 dark:text-gray-100 overflow-auto max-h-[500px] whitespace-pre-wrap font-mono border border-gray-200 dark:border-gray-700">
      {decodedContent}
    </pre>
  );
}

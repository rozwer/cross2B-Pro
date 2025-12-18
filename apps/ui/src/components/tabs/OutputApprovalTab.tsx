"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  FileText,
  Code,
  ImageIcon,
  File,
  Download,
  ExternalLink,
  Check,
  X,
  RotateCcw,
  Eye,
  Wifi,
  WifiOff,
  Plus,
  Search,
  Filter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDate, formatBytes } from "@/lib/utils";
import type { Run, RunSummary, Step, StepStatus, ArtifactRef, ArtifactContent } from "@/lib/types";
import { useRuns } from "@/hooks/useRuns";
import { useRun } from "@/hooks/useRun";
import { useRunProgress } from "@/hooks/useRunProgress";
import { useArtifacts } from "@/hooks/useArtifact";
import { api } from "@/lib/api";
import { Loading, LoadingPage } from "@/components/common/Loading";
import { ApprovalDialog } from "@/components/common/ApprovalDialog";
import { JsonViewer } from "@/components/artifacts/JsonViewer";
import { MarkdownViewer } from "@/components/artifacts/MarkdownViewer";
import { HtmlPreview } from "@/components/artifacts/HtmlPreview";
import { STEP_LABELS } from "@/lib/types";

interface OutputApprovalTabProps {
  onCreateRun?: () => void;
}

const STATUS_CONFIG: Record<
  string,
  { bg: string; text: string; icon: React.ReactNode; label: string }
> = {
  pending: {
    bg: "bg-gray-100",
    text: "text-gray-700",
    icon: <Clock className="h-3.5 w-3.5" />,
    label: "待機中",
  },
  running: {
    bg: "bg-blue-100",
    text: "text-blue-700",
    icon: <Play className="h-3.5 w-3.5 animate-pulse" />,
    label: "実行中",
  },
  waiting_approval: {
    bg: "bg-yellow-100",
    text: "text-yellow-700",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    label: "承認待ち",
  },
  completed: {
    bg: "bg-green-100",
    text: "text-green-700",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    label: "完了",
  },
  failed: {
    bg: "bg-red-100",
    text: "text-red-700",
    icon: <XCircle className="h-3.5 w-3.5" />,
    label: "失敗",
  },
  cancelled: {
    bg: "bg-gray-100",
    text: "text-gray-500",
    icon: <X className="h-3.5 w-3.5" />,
    label: "キャンセル",
  },
};

const STEP_STATUS_CONFIG: Record<StepStatus, { bg: string; text: string; icon: React.ReactNode }> =
  {
    pending: {
      bg: "bg-gray-50",
      text: "text-gray-600",
      icon: <Clock className="h-3.5 w-3.5 text-gray-400" />,
    },
    running: {
      bg: "bg-blue-50",
      text: "text-blue-700",
      icon: <Play className="h-3.5 w-3.5 text-blue-500 animate-pulse" />,
    },
    completed: {
      bg: "bg-green-50",
      text: "text-green-700",
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
    },
    failed: {
      bg: "bg-red-50",
      text: "text-red-700",
      icon: <XCircle className="h-3.5 w-3.5 text-red-500" />,
    },
    skipped: {
      bg: "bg-gray-50",
      text: "text-gray-500",
      icon: <Clock className="h-3.5 w-3.5 text-gray-400" />,
    },
  };

export function OutputApprovalTab({ onCreateRun }: OutputApprovalTabProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const { runs, loading: runsLoading, fetch: fetchRuns } = useRuns();

  // Filter runs
  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    return runs.filter((run) => {
      const matchesSearch =
        searchQuery === "" ||
        run.keyword.toLowerCase().includes(searchQuery.toLowerCase()) ||
        run.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = filterStatus === "all" || run.status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [runs, searchQuery, filterStatus]);

  // Auto-select first run
  useEffect(() => {
    if (!selectedRunId && filteredRuns.length > 0) {
      setSelectedRunId(filteredRuns[0].id);
    }
  }, [filteredRuns, selectedRunId]);

  return (
    <div className="h-full flex gap-4">
      {/* Runs List (Left Panel) */}
      <div className="w-80 flex-shrink-0 flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* List Header */}
        <div className="p-3 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">実行一覧</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchRuns()}
                className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                title="更新"
              >
                <RefreshCw className="h-4 w-4 text-gray-500" />
              </button>
              {onCreateRun && (
                <button
                  onClick={onCreateRun}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" />
                  新規
                </button>
              )}
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <input
              type="text"
              placeholder="検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {/* Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full px-2 py-1.5 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="all">すべてのステータス</option>
            <option value="running">実行中</option>
            <option value="waiting_approval">承認待ち</option>
            <option value="completed">完了</option>
            <option value="failed">失敗</option>
          </select>
        </div>

        {/* Runs List */}
        <div className="flex-1 overflow-y-auto">
          {runsLoading ? (
            <div className="p-8">
              <Loading text="読み込み中..." />
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              {searchQuery || filterStatus !== "all"
                ? "条件に一致するRunがありません"
                : "Runがありません"}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredRuns.map((run) => {
                const status = STATUS_CONFIG[run.status] || STATUS_CONFIG.pending;
                const isSelected = run.id === selectedRunId;

                return (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    className={cn(
                      "w-full text-left px-3 py-3 transition-colors",
                      isSelected
                        ? "bg-primary-50 border-l-2 border-primary-500"
                        : "hover:bg-gray-50",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p
                        className={cn(
                          "font-medium truncate",
                          isSelected ? "text-primary-700" : "text-gray-900",
                        )}
                      >
                        {run.keyword}
                      </p>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs flex-shrink-0",
                          status.bg,
                          status.text,
                        )}
                      >
                        {status.icon}
                        {status.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>{run.id.slice(0, 8)}</span>
                      <span>•</span>
                      <span>{formatDate(run.created_at)}</span>
                    </div>
                    {run.current_step && (
                      <p className="text-xs text-gray-400 mt-1">
                        現在: {STEP_LABELS[run.current_step] || run.current_step}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Run Detail (Right Panel) */}
      <div className="flex-1 min-w-0">
        {selectedRunId ? (
          <RunDetailPanel runId={selectedRunId} />
        ) : (
          <div className="h-full flex items-center justify-center bg-white rounded-lg border border-gray-200">
            <div className="text-center text-gray-500">
              <Eye className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>Runを選択してください</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Run Detail Panel Component
function RunDetailPanel({ runId }: { runId: string }) {
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);

  const { run, loading, error, fetch, approve, reject, retry } = useRun(runId);
  const { events, wsStatus } = useRunProgress(runId, {
    onEvent: (event) => {
      if (
        event.type === "step_completed" ||
        event.type === "step_failed" ||
        event.type === "run_completed"
      ) {
        fetch();
      }
    },
  });
  const { artifacts, fetch: fetchArtifacts } = useArtifacts(runId);

  // Auto-expand current step
  useEffect(() => {
    if (run?.current_step) {
      setExpandedSteps((prev) => new Set([...Array.from(prev), run.current_step as string]));
    }
  }, [run?.current_step]);

  // Fetch artifacts when run loads
  useEffect(() => {
    if (run) {
      fetchArtifacts();
    }
  }, [run, fetchArtifacts]);

  const toggleStep = (stepName: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepName)) {
      newExpanded.delete(stepName);
    } else {
      newExpanded.add(stepName);
    }
    setExpandedSteps(newExpanded);
    setSelectedStep(stepName);
  };

  const handleApprove = async () => {
    setApprovalLoading(true);
    try {
      await approve();
      setShowApprovalDialog(false);
    } catch (err) {
      console.error("Approval failed:", err);
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleReject = async (reason: string) => {
    setApprovalLoading(true);
    try {
      await reject(reason);
      setShowApprovalDialog(false);
    } catch (err) {
      console.error("Rejection failed:", err);
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleRetry = async (stepName: string) => {
    try {
      await retry(stepName);
    } catch (err) {
      console.error("Retry failed:", err);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-white rounded-lg border border-gray-200">
        <Loading text="読み込み中..." />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="h-full flex items-center justify-center bg-white rounded-lg border border-gray-200">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-red-300 mx-auto mb-3" />
          <p className="text-gray-700 mb-2">{error || "Run not found"}</p>
          <button
            onClick={fetch}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors text-sm"
          >
            <RefreshCw className="h-4 w-4" />
            再試行
          </button>
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[run.status] || STATUS_CONFIG.pending;
  const progress = run.steps.filter((s) => s.status === "completed").length;
  const total = run.steps.length;

  // Group artifacts by step_name (fallback to step_id for backwards compatibility)
  const artifactsByStep = artifacts.reduce(
    (acc, artifact) => {
      const stepKey = artifact.step_name || artifact.step_id;
      if (!acc[stepKey]) acc[stepKey] = [];
      acc[stepKey].push(artifact);
      return acc;
    },
    {} as Record<string, ArtifactRef[]>,
  );

  return (
    <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900 truncate">{run.input.keyword}</h2>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 px-2 py-1 rounded text-sm",
                statusConfig.bg,
                statusConfig.text,
              )}
            >
              {statusConfig.icon}
              {statusConfig.label}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1 text-xs",
                wsStatus === "connected" ? "text-green-600" : "text-gray-400",
              )}
            >
              {wsStatus === "connected" ? (
                <Wifi className="h-3.5 w-3.5" />
              ) : (
                <WifiOff className="h-3.5 w-3.5" />
              )}
              {wsStatus}
            </span>
            <button onClick={fetch} className="p-1.5 hover:bg-gray-200 rounded transition-colors">
              <RefreshCw className="h-4 w-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full transition-all duration-500",
                run.status === "failed" ? "bg-red-500" : "bg-primary-500",
              )}
              style={{ width: `${(progress / total) * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">
            {progress}/{total} 完了
          </span>
        </div>

        {/* Approval Actions */}
        {run.status === "waiting_approval" && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <span className="font-medium text-yellow-800">承認が必要です</span>
              </div>
              <button
                onClick={() => setShowApprovalDialog(true)}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm font-medium"
              >
                <Eye className="h-4 w-4" />
                成果物を確認して承認
              </button>
            </div>
          </div>
        )}

        {/* Approval Dialog */}
        <ApprovalDialog
          isOpen={showApprovalDialog}
          onClose={() => setShowApprovalDialog(false)}
          onApprove={handleApprove}
          onReject={handleReject}
          runId={runId}
          artifacts={artifacts}
          loading={approvalLoading}
        />
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-100">
          {run.steps.map((step) => {
            const isExpanded = expandedSteps.has(step.step_name);
            const isCurrent = run.current_step === step.step_name;
            const stepStatusConfig = STEP_STATUS_CONFIG[step.status];
            const stepArtifacts = artifactsByStep[step.step_name] || [];
            const stepLabel = STEP_LABELS[step.step_name] || step.step_name;

            return (
              <div key={step.id} className={cn(isCurrent && "bg-blue-50/50")}>
                {/* Step Header */}
                <button
                  onClick={() => toggleStep(step.step_name)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50",
                    isExpanded && "bg-gray-50",
                  )}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  )}

                  <div
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                      stepStatusConfig.bg,
                    )}
                  >
                    {stepStatusConfig.icon}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn("font-medium", stepStatusConfig.text)}>{stepLabel}</span>
                      <span className="text-xs text-gray-400">{step.step_name}</span>
                      {isCurrent && (
                        <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                          現在
                        </span>
                      )}
                    </div>
                    {step.started_at && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {formatDate(step.started_at)}
                        {step.completed_at && ` → ${formatDate(step.completed_at)}`}
                      </p>
                    )}
                  </div>

                  {/* Artifacts Count */}
                  {stepArtifacts.length > 0 && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {stepArtifacts.length} 成果物
                    </span>
                  )}

                  {/* Retry Button */}
                  {step.status === "failed" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRetry(step.step_name);
                      }}
                      className="p-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                      title="リトライ"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                    </button>
                  )}
                </button>

                {/* Step Detail (Expanded) */}
                {isExpanded && (
                  <div className="px-4 pb-4 bg-gray-50 border-t border-gray-100">
                    {/* Attempts */}
                    {step.attempts.length > 0 && (
                      <div className="mt-3">
                        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">
                          試行履歴
                        </h5>
                        <div className="space-y-2">
                          {step.attempts.map((attempt, index) => (
                            <div
                              key={attempt.id}
                              className={cn(
                                "p-2 rounded border",
                                attempt.status === "succeeded" && "bg-green-50 border-green-200",
                                attempt.status === "failed" && "bg-red-50 border-red-200",
                                attempt.status === "running" && "bg-blue-50 border-blue-200",
                              )}
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-medium">
                                  試行 #{attempt.attempt_num}
                                </span>
                                <span
                                  className={cn(
                                    "text-xs",
                                    attempt.status === "succeeded" && "text-green-700",
                                    attempt.status === "failed" && "text-red-700",
                                    attempt.status === "running" && "text-blue-700",
                                  )}
                                >
                                  {attempt.status === "succeeded" && "成功"}
                                  {attempt.status === "failed" && "失敗"}
                                  {attempt.status === "running" && "実行中"}
                                </span>
                              </div>
                              {attempt.error && (
                                <p className="text-xs text-red-600 mt-1">{attempt.error.message}</p>
                              )}
                              {attempt.repairs && attempt.repairs.length > 0 && (
                                <div className="mt-1">
                                  <span className="text-xs text-gray-500">修正適用:</span>
                                  {attempt.repairs.map((repair, i) => (
                                    <span key={i} className="text-xs text-gray-600 ml-1">
                                      {repair.description}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Validation Report */}
                    {step.validation_report && (
                      <div className="mt-3">
                        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">
                          検証結果
                        </h5>
                        <div
                          className={cn(
                            "p-2 rounded border",
                            step.validation_report.valid
                              ? "bg-green-50 border-green-200"
                              : "bg-red-50 border-red-200",
                          )}
                        >
                          <div className="flex items-center gap-2">
                            {step.validation_report.valid ? (
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-600" />
                            )}
                            <span
                              className={cn(
                                "text-sm font-medium",
                                step.validation_report.valid ? "text-green-700" : "text-red-700",
                              )}
                            >
                              {step.validation_report.valid ? "パス" : "失敗"}
                            </span>
                          </div>
                          {step.validation_report.errors.length > 0 && (
                            <ul className="mt-2 text-xs text-red-600 list-disc list-inside">
                              {step.validation_report.errors.slice(0, 3).map((err, i) => (
                                <li key={i}>{err.message}</li>
                              ))}
                              {step.validation_report.errors.length > 3 && (
                                <li>...他 {step.validation_report.errors.length - 3} 件</li>
                              )}
                            </ul>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Artifacts */}
                    {stepArtifacts.length > 0 && (
                      <div className="mt-3">
                        <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">成果物</h5>
                        <StepArtifactsList runId={runId} artifacts={stepArtifacts} />
                      </div>
                    )}

                    {/* Empty State */}
                    {step.attempts.length === 0 &&
                      !step.validation_report &&
                      stepArtifacts.length === 0 && (
                        <div className="mt-3 text-center py-4 text-gray-400 text-sm">
                          このステップはまだ開始されていません
                        </div>
                      )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Artifacts List Component
function StepArtifactsList({ runId, artifacts }: { runId: string; artifacts: ArtifactRef[] }) {
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [loading, setLoading] = useState(false);

  const loadContent = async (artifact: ArtifactRef) => {
    setSelectedArtifact(artifact);
    setLoading(true);
    try {
      const data = await api.artifacts.download(runId, artifact.id);
      setContent(data);
    } catch (err) {
      console.error("Failed to load artifact:", err);
      setContent(null);
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (contentType: string) => {
    if (contentType.includes("json")) return <Code className="h-4 w-4" />;
    if (contentType.includes("html")) return <FileText className="h-4 w-4" />;
    if (contentType.includes("markdown")) return <FileText className="h-4 w-4" />;
    if (contentType.includes("image")) return <ImageIcon className="h-4 w-4" />;
    return <File className="h-4 w-4" />;
  };

  return (
    <div>
      {/* Artifacts Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {artifacts.map((artifact) => (
          <button
            key={artifact.id}
            onClick={() => loadContent(artifact)}
            className={cn(
              "flex items-center gap-2 p-2 rounded border text-left text-sm transition-colors",
              selectedArtifact?.id === artifact.id
                ? "bg-primary-50 border-primary-300"
                : "bg-white border-gray-200 hover:border-gray-300",
            )}
          >
            {getIcon(artifact.content_type)}
            <div className="flex-1 min-w-0">
              <p className="truncate text-xs font-medium text-gray-700">
                {artifact.ref_path.split("/").pop()}
              </p>
              <p className="text-xs text-gray-400">{formatBytes(artifact.size_bytes)}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Content Preview */}
      {selectedArtifact && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
            <span className="text-xs text-gray-600 truncate">{selectedArtifact.ref_path}</span>
            <a
              href={`data:${selectedArtifact.content_type};base64,${content?.encoding === "base64" ? content?.content : btoa(content?.content || "")}`}
              download={selectedArtifact.ref_path.split("/").pop()}
              className="text-xs text-primary-600 hover:underline flex items-center gap-1"
            >
              <Download className="h-3 w-3" />
              ダウンロード
            </a>
          </div>
          <div className="max-h-64 overflow-auto">
            {loading ? (
              <div className="p-4">
                <Loading text="読み込み中..." />
              </div>
            ) : content ? (
              <ContentRenderer
                content={content.content}
                contentType={selectedArtifact.content_type}
                encoding={content.encoding}
              />
            ) : (
              <div className="p-4 text-center text-gray-400 text-sm">
                コンテンツを読み込めませんでした
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Content Renderer
function ContentRenderer({
  content,
  contentType,
  encoding,
}: {
  content: string;
  contentType: string;
  encoding: "utf-8" | "base64";
}) {
  const decodedContent = encoding === "base64" ? atob(content) : content;

  if (contentType.includes("json")) {
    return (
      <div className="p-2">
        <JsonViewer content={decodedContent} />
      </div>
    );
  }

  if (contentType.includes("html")) {
    return (
      <div className="p-2">
        <HtmlPreview content={decodedContent} />
      </div>
    );
  }

  if (contentType.includes("markdown")) {
    return (
      <div className="p-2">
        <MarkdownViewer content={decodedContent} />
      </div>
    );
  }

  return (
    <pre className="p-3 bg-gray-50 text-xs overflow-auto whitespace-pre-wrap text-gray-700">
      {decodedContent.slice(0, 2000)}
      {decodedContent.length > 2000 && "..."}
    </pre>
  );
}

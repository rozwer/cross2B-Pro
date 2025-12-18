"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
  MiniMap,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Play,
  Pause,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StepConfig } from "@/components/workflow/NodeConfigPanel";
import type { Step, StepStatus, RunStatus } from "@/lib/types";
import type { LLMPlatform } from "@/lib/types";

interface GraphViewTabProps {
  stepConfigs: StepConfig[];
  onNodeClick?: (stepId: string) => void;
  runStatus?: RunStatus;
  runSteps?: Step[];
  currentStep?: string;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

// Node data type for workflow
interface WorkflowNodeData extends Record<string, unknown> {
  stepId: string;
  label: string;
  description: string;
  aiModel: LLMPlatform;
  modelName: string;
  status: StepStatus | "pending";
  stepType: "input" | "analysis" | "generation" | "verification" | "output" | "approval";
  isParallel?: boolean;
  isApprovalPoint?: boolean;
  isCurrent?: boolean;
  onNodeClick?: (stepId: string) => void;
}

type WorkflowNode = Node<WorkflowNodeData>;

const HORIZONTAL_GAP = 250;
const VERTICAL_GAP = 150;

const PLATFORM_COLORS: Record<LLMPlatform, { bg: string; border: string; text: string }> = {
  gemini: { bg: "bg-blue-100", border: "border-blue-400", text: "text-blue-700" },
  anthropic: { bg: "bg-orange-100", border: "border-orange-400", text: "text-orange-700" },
  openai: { bg: "bg-green-100", border: "border-green-400", text: "text-green-700" },
};

const STATUS_COLORS: Record<string, { bg: string; border: string; icon: React.ReactNode }> = {
  pending: {
    bg: "bg-gray-100",
    border: "border-gray-300",
    icon: <Clock className="h-4 w-4 text-gray-400" />,
  },
  running: {
    bg: "bg-blue-100",
    border: "border-blue-500",
    icon: <Play className="h-4 w-4 text-blue-600 animate-pulse" />,
  },
  completed: {
    bg: "bg-green-100",
    border: "border-green-500",
    icon: <CheckCircle2 className="h-4 w-4 text-green-600" />,
  },
  failed: {
    bg: "bg-red-100",
    border: "border-red-500",
    icon: <XCircle className="h-4 w-4 text-red-600" />,
  },
  skipped: {
    bg: "bg-gray-100",
    border: "border-gray-300",
    icon: <Pause className="h-4 w-4 text-gray-400" />,
  },
};

// Custom Node Component
function CustomWorkflowNode({ data }: { data: WorkflowNodeData }) {
  const platformColors = PLATFORM_COLORS[data.aiModel];
  const statusInfo = STATUS_COLORS[data.status] || STATUS_COLORS.pending;

  return (
    <div
      onClick={() => data.onNodeClick?.(data.stepId)}
      className={cn(
        "min-w-[180px] rounded-xl border-2 shadow-sm transition-all cursor-pointer hover:shadow-md",
        data.isApprovalPoint
          ? "border-yellow-400 bg-yellow-50"
          : data.isCurrent
            ? "ring-2 ring-blue-500 ring-offset-2 " + statusInfo.bg + " " + statusInfo.border
            : statusInfo.bg + " " + statusInfo.border,
        data.isParallel && "border-dashed",
      )}
    >
      {/* Header */}
      <div
        className={cn(
          "px-3 py-2 border-b flex items-center justify-between",
          data.isApprovalPoint ? "border-yellow-200" : "border-gray-200",
        )}
      >
        <div className="flex items-center gap-2">
          {statusInfo.icon}
          <span className="font-medium text-gray-900 text-sm">{data.label}</span>
        </div>
        {data.isParallel && (
          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">並列</span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <p className="text-xs text-gray-500 mb-2 line-clamp-2">{data.description}</p>

        {/* Model Info */}
        {!data.isApprovalPoint && (
          <div
            className={cn(
              "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs",
              platformColors.bg,
              platformColors.text,
            )}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor:
                  data.aiModel === "gemini"
                    ? "#3b82f6"
                    : data.aiModel === "anthropic"
                      ? "#f97316"
                      : "#22c55e",
              }}
            />
            <span>{data.modelName || data.aiModel}</span>
          </div>
        )}

        {data.isApprovalPoint && (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-yellow-100 text-yellow-700">
            <AlertTriangle className="h-3 w-3" />
            <span>人間確認</span>
          </div>
        )}
      </div>

      {/* Step ID Footer */}
      <div className="px-3 py-1 bg-gray-50 border-t border-gray-100 rounded-b-xl">
        <span className="text-xs text-gray-400">{data.stepId}</span>
      </div>
    </div>
  );
}

const nodeTypes = {
  workflowNode: CustomWorkflowNode,
};

function createNodes(
  steps: StepConfig[],
  runSteps: Step[] | undefined,
  currentStep: string | undefined,
  onNodeClick?: (stepId: string) => void,
): WorkflowNode[] {
  const nodes: WorkflowNode[] = [];

  const getStepStatus = (stepId: string): StepStatus | "pending" => {
    if (!runSteps) return "pending";
    const step = runSteps.find((s) => s.step_name === stepId);
    return step?.status || "pending";
  };

  // Row 1: step-1, step0, step1, step2
  const row1Steps = ["step-1", "step0", "step1", "step2"];
  row1Steps.forEach((stepId, index) => {
    const step = steps.find((s) => s.stepId === stepId);
    if (step) {
      nodes.push({
        id: stepId,
        type: "workflowNode",
        position: { x: index * HORIZONTAL_GAP, y: 0 },
        data: {
          stepId: step.stepId,
          label: step.label,
          description: step.description,
          aiModel: step.aiModel,
          modelName: step.modelName,
          status: getStepStatus(stepId),
          stepType: stepId === "step-1" ? "input" : "analysis",
          isCurrent: currentStep === stepId,
          onNodeClick,
        },
      });
    }
  });

  // Row 2: Parallel steps 3a, 3b, 3c
  const row2Steps = ["step3a", "step3b", "step3c"];
  row2Steps.forEach((stepId, index) => {
    const step = steps.find((s) => s.stepId === stepId);
    if (step) {
      nodes.push({
        id: stepId,
        type: "workflowNode",
        position: { x: (index + 0.5) * HORIZONTAL_GAP, y: VERTICAL_GAP },
        data: {
          stepId: step.stepId,
          label: step.label,
          description: step.description,
          aiModel: step.aiModel,
          modelName: step.modelName,
          status: getStepStatus(stepId),
          isParallel: true,
          stepType: "analysis",
          isCurrent: currentStep === stepId,
          onNodeClick,
        },
      });
    }
  });

  // Row 3: Approval point
  const approvalStep = steps.find((s) => s.stepId === "approval");
  if (approvalStep) {
    nodes.push({
      id: "approval",
      type: "workflowNode",
      position: { x: 1.5 * HORIZONTAL_GAP, y: 2 * VERTICAL_GAP },
      data: {
        stepId: "approval",
        label: approvalStep.label,
        description: approvalStep.description,
        aiModel: "gemini",
        modelName: "",
        status: getStepStatus("approval"),
        isApprovalPoint: true,
        stepType: "approval",
        isCurrent: currentStep === "approval",
        onNodeClick,
      },
    });
  }

  // Row 4-6: Sequential steps after approval
  const postApprovalSteps = [
    ["step4", "step5", "step6", "step6.5"],
    ["step7a", "step7b", "step8"],
    ["step9", "step10"],
  ];

  postApprovalSteps.forEach((rowSteps, rowIndex) => {
    rowSteps.forEach((stepId, colIndex) => {
      const step = steps.find((s) => s.stepId === stepId);
      if (step) {
        const offsetX = rowIndex === 2 ? 0.75 : rowIndex === 1 ? 0.5 : 0;
        nodes.push({
          id: stepId,
          type: "workflowNode",
          position: {
            x: (colIndex + offsetX) * HORIZONTAL_GAP,
            y: (3 + rowIndex) * VERTICAL_GAP,
          },
          data: {
            stepId: step.stepId,
            label: step.label,
            description: step.description,
            aiModel: step.aiModel,
            modelName: step.modelName,
            status: getStepStatus(stepId),
            stepType:
              stepId === "step10" ? "output" : stepId === "step8" ? "verification" : "generation",
            isCurrent: currentStep === stepId,
            onNodeClick,
          },
        });
      }
    });
  });

  return nodes;
}

function createEdges(runSteps?: Step[]): Edge[] {
  const getEdgeStyle = (sourceId: string, targetId: string) => {
    if (!runSteps) return {};

    const sourceStep = runSteps.find((s) => s.step_name === sourceId);
    const targetStep = runSteps.find((s) => s.step_name === targetId);

    if (sourceStep?.status === "completed" && targetStep?.status === "completed") {
      return { stroke: "#22c55e", strokeWidth: 2 };
    }
    if (sourceStep?.status === "completed" && targetStep?.status === "running") {
      return { stroke: "#3b82f6", strokeWidth: 2 };
    }
    if (sourceStep?.status === "failed" || targetStep?.status === "failed") {
      return { stroke: "#ef4444", strokeWidth: 2 };
    }
    return {};
  };

  return [
    // Row 1 connections
    {
      id: "e-step-1-step0",
      source: "step-1",
      target: "step0",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step-1", "step0"),
    },
    {
      id: "e-step0-step1",
      source: "step0",
      target: "step1",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step0", "step1"),
    },
    {
      id: "e-step1-step2",
      source: "step1",
      target: "step2",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step1", "step2"),
    },
    // Fan-out to parallel steps
    {
      id: "e-step2-step3a",
      source: "step2",
      target: "step3a",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step2", "step3a"),
    },
    {
      id: "e-step2-step3b",
      source: "step2",
      target: "step3b",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step2", "step3b"),
    },
    {
      id: "e-step2-step3c",
      source: "step2",
      target: "step3c",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step2", "step3c"),
    },
    // Fan-in to approval
    {
      id: "e-step3a-approval",
      source: "step3a",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step3a", "approval"),
    },
    {
      id: "e-step3b-approval",
      source: "step3b",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step3b", "approval"),
    },
    {
      id: "e-step3c-approval",
      source: "step3c",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step3c", "approval"),
    },
    // After approval - Row 4
    {
      id: "e-approval-step4",
      source: "approval",
      target: "step4",
      animated: true,
      style: { ...getEdgeStyle("approval", "step4"), strokeDasharray: "5,5" },
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step4-step5",
      source: "step4",
      target: "step5",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step4", "step5"),
    },
    {
      id: "e-step5-step6",
      source: "step5",
      target: "step6",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step5", "step6"),
    },
    {
      id: "e-step6-step6.5",
      source: "step6",
      target: "step6.5",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step6", "step6.5"),
    },
    // Row 5
    {
      id: "e-step6.5-step7a",
      source: "step6.5",
      target: "step7a",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step6.5", "step7a"),
    },
    {
      id: "e-step7a-step7b",
      source: "step7a",
      target: "step7b",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step7a", "step7b"),
    },
    {
      id: "e-step7b-step8",
      source: "step7b",
      target: "step8",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step7b", "step8"),
    },
    // Row 6
    {
      id: "e-step8-step9",
      source: "step8",
      target: "step9",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step8", "step9"),
    },
    {
      id: "e-step9-step10",
      source: "step9",
      target: "step10",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: getEdgeStyle("step9", "step10"),
    },
  ];
}

export function GraphViewTab({
  stepConfigs,
  onNodeClick,
  runStatus,
  runSteps,
  currentStep,
  isFullscreen = false,
  onToggleFullscreen,
}: GraphViewTabProps) {
  const initialNodes = useMemo(
    () => createNodes(stepConfigs, runSteps, currentStep, onNodeClick),
    [stepConfigs, runSteps, currentStep, onNodeClick],
  );

  const initialEdges = useMemo(() => createEdges(runSteps), [runSteps]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when runSteps or currentStep changes
  useEffect(() => {
    setNodes(createNodes(stepConfigs, runSteps, currentStep, onNodeClick));
    setEdges(createEdges(runSteps));
  }, [stepConfigs, runSteps, currentStep, onNodeClick, setNodes, setEdges]);

  // Calculate progress
  const progress = useMemo(() => {
    if (!runSteps || runSteps.length === 0) return 0;
    const completed = runSteps.filter((s) => s.status === "completed").length;
    return Math.round((completed / stepConfigs.length) * 100);
  }, [runSteps, stepConfigs.length]);

  return (
    <div
      className={cn(
        "flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden",
        isFullscreen ? "fixed inset-0 z-50" : "h-full",
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-4">
          {/* Run Status */}
          {runStatus && (
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "px-2 py-1 rounded text-xs font-medium",
                  runStatus === "running" && "bg-blue-100 text-blue-700",
                  runStatus === "completed" && "bg-green-100 text-green-700",
                  runStatus === "failed" && "bg-red-100 text-red-700",
                  runStatus === "waiting_approval" && "bg-yellow-100 text-yellow-700",
                  runStatus === "pending" && "bg-gray-100 text-gray-700",
                )}
              >
                {runStatus === "running" && "実行中"}
                {runStatus === "completed" && "完了"}
                {runStatus === "failed" && "失敗"}
                {runStatus === "waiting_approval" && "承認待ち"}
                {runStatus === "pending" && "待機中"}
              </span>
              <span className="text-sm text-gray-500">{progress}%</span>
            </div>
          )}

          {/* Current Step */}
          {currentStep && (
            <span className="text-sm text-gray-600">
              現在:{" "}
              <strong>
                {stepConfigs.find((s) => s.stepId === currentStep)?.label || currentStep}
              </strong>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onToggleFullscreen && (
            <button
              onClick={onToggleFullscreen}
              className="p-2 hover:bg-gray-200 rounded transition-colors"
              title={isFullscreen ? "縮小" : "全画面"}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4 text-gray-600" />
              ) : (
                <Maximize2 className="h-4 w-4 text-gray-600" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
          <Controls
            position="bottom-left"
            showInteractive={false}
            className="!bg-white !border-gray-200 !shadow-md"
          />
          <MiniMap
            position="bottom-right"
            nodeStrokeWidth={3}
            className="!bg-white !border-gray-200 !shadow-md"
            maskColor="rgba(0,0,0,0.1)"
          />
        </ReactFlow>

        {/* Legend */}
        <div className="absolute top-4 right-4 bg-white rounded-lg border border-gray-200 shadow-sm p-3">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">凡例</h4>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-blue-400" />
              <span className="text-gray-600">Gemini</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-orange-400" />
              <span className="text-gray-600">Claude</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-green-400" />
              <span className="text-gray-600">OpenAI</span>
            </div>
          </div>
          <div className="border-t border-gray-200 mt-2 pt-2 space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              <span className="text-gray-600">完了</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <Play className="w-3 h-3 text-blue-500" />
              <span className="text-gray-600">実行中</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <Clock className="w-3 h-3 text-gray-400" />
              <span className="text-gray-600">待機中</span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar (when running) */}
      {runStatus === "running" && (
        <div className="h-1 bg-gray-200">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

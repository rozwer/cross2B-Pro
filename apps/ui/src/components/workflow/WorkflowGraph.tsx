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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { WorkflowNode, type WorkflowNodeData } from "./WorkflowNode";
import { NodeConfigPanel, type StepConfig } from "./NodeConfigPanel";
import { useModelsConfig } from "@/hooks/useModelsConfig";
import type { StepDefaultConfig } from "@/lib/types";

/**
 * Convert backend StepDefaultConfig to frontend StepConfig format
 */
function convertToStepConfig(backendConfig: StepDefaultConfig): StepConfig {
  return {
    stepId: backendConfig.step_id,
    label: backendConfig.label,
    description: backendConfig.description,
    aiModel: backendConfig.ai_model,
    modelName: backendConfig.model_name,
    temperature: backendConfig.temperature,
    grounding: backendConfig.grounding,
    retryLimit: backendConfig.retry_limit,
    repairEnabled: backendConfig.repair_enabled,
    isConfigurable: backendConfig.is_configurable,
    recommendedModel: backendConfig.recommended_model,
  };
}

// Fallback step definitions (used only if backend is unavailable)
const FALLBACK_WORKFLOW_STEPS: StepConfig[] = [
  {
    stepId: "step-1",
    label: "入力",
    description: "キーワードとターゲット情報の入力",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: false,
    recommendedModel: "gemini",
  },
  {
    stepId: "step0",
    label: "キーワード選定",
    description: "キーワードの分析と最適化",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step1",
    label: "競合記事取得",
    description: "SERP分析と競合コンテンツの収集",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.5,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step1_5",
    label: "関連KW抽出",
    description: "関連キーワードの競合情報収集",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.6,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step2",
    label: "CSV検証",
    description: "取得データの形式検証",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.3,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step3a",
    label: "クエリ分析",
    description: "検索クエリとペルソナの分析",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step3b",
    label: "共起語抽出",
    description: "関連キーワードと共起語の抽出",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step3c",
    label: "競合分析",
    description: "競合記事の差別化ポイント分析",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "approval",
    label: "承認待ち",
    description: "人間による確認・承認ポイント",
    aiModel: "gemini",
    modelName: "",
    temperature: 0,
    grounding: false,
    retryLimit: 1,
    repairEnabled: false,
    isConfigurable: false,
    recommendedModel: "gemini",
  },
  {
    stepId: "step3_5",
    label: "人間味生成",
    description: "心情傾向・体験エピソードの生成",
    aiModel: "gemini",
    modelName: "gemini-1.5-pro",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step4",
    label: "アウトライン",
    description: "戦略的な記事構成の作成",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step5",
    label: "一次情報収集",
    description: "Web検索による一次情報の収集",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.5,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step6",
    label: "アウトライン強化",
    description: "一次情報を組み込んだ構成改善",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step6_5",
    label: "統合パッケージ",
    description: "全情報の統合とパッケージ化",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.5,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step7a",
    label: "本文生成",
    description: "初稿の本文生成",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.8,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step7b",
    label: "ブラッシュアップ",
    description: "文章の磨き上げと最適化",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.6,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step8",
    label: "ファクトチェック",
    description: "事実確認とFAQ生成",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.3,
    grounding: true,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step9",
    label: "最終リライト",
    description: "品質管理と最終調整",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.5,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step10",
    label: "最終出力",
    description: "HTML/Markdown形式での出力",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.3,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
  {
    stepId: "step11",
    label: "画像生成",
    description: "AI画像生成と記事への挿入",
    aiModel: "gemini",
    modelName: "gemini-2.0-flash",
    temperature: 0.7,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "gemini",
  },
  {
    stepId: "step12",
    label: "WordPress HTML",
    description: "Gutenbergブロック形式でのHTML生成",
    aiModel: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.3,
    grounding: false,
    retryLimit: 3,
    repairEnabled: true,
    isConfigurable: true,
    recommendedModel: "anthropic",
  },
];

// Layout positions
const HORIZONTAL_GAP = 250;
const VERTICAL_GAP = 150;

type WorkflowNode = Node<WorkflowNodeData>;

function createInitialNodes(
  steps: StepConfig[],
  onNodeClick: (stepId: string) => void,
): WorkflowNode[] {
  const nodes: WorkflowNode[] = [];

  // Row 1: step-1, step0, step1, step1_5, step2
  const row1Steps = ["step-1", "step0", "step1", "step1_5", "step2"];
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
          status: "pending",
          stepType: stepId === "step-1" ? "input" : "analysis",
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
          status: "pending",
          isParallel: true,
          stepType: "analysis",
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
        status: "pending",
        isApprovalPoint: true,
        stepType: "approval",
        onNodeClick,
      },
    });
  }

  // Row 4-6: Sequential steps after approval
  const postApprovalSteps = [
    ["step3_5", "step4", "step5", "step6"],
    ["step6_5", "step7a", "step7b", "step8"],
    ["step9", "step10", "step11", "step12"],
  ];

  postApprovalSteps.forEach((rowSteps, rowIndex) => {
    rowSteps.forEach((stepId, colIndex) => {
      const step = steps.find((s) => s.stepId === stepId);
      if (step) {
        const offsetX = rowSteps.length === 3 ? 0.5 : rowSteps.length === 2 ? 0.75 : 0;
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
            status: "pending",
            stepType:
              stepId === "step10" || stepId === "step11" || stepId === "step12"
                ? "output"
                : stepId === "step8"
                  ? "verification"
                  : "generation",
            onNodeClick,
          },
        });
      }
    });
  });

  return nodes;
}

function createInitialEdges(): Edge[] {
  return [
    // Row 1 connections
    {
      id: "e-step-1-step0",
      source: "step-1",
      target: "step0",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step0-step1",
      source: "step0",
      target: "step1",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step1-step1_5",
      source: "step1",
      target: "step1_5",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step1_5-step2",
      source: "step1_5",
      target: "step2",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    // Fan-out to parallel steps
    {
      id: "e-step2-step3a",
      source: "step2",
      target: "step3a",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step2-step3b",
      source: "step2",
      target: "step3b",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step2-step3c",
      source: "step2",
      target: "step3c",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    // Fan-in to approval
    {
      id: "e-step3a-approval",
      source: "step3a",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step3b-approval",
      source: "step3b",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step3c-approval",
      source: "step3c",
      target: "approval",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    // After approval - Row 4
    {
      id: "e-approval-step3_5",
      source: "approval",
      target: "step3_5",
      animated: true,
      style: { strokeDasharray: "5,5" },
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step3_5-step4",
      source: "step3_5",
      target: "step4",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step4-step5",
      source: "step4",
      target: "step5",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step5-step6",
      source: "step5",
      target: "step6",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step6-step6_5",
      source: "step6",
      target: "step6_5",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    // Row 5
    {
      id: "e-step6_5-step7a",
      source: "step6_5",
      target: "step7a",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step7a-step7b",
      source: "step7a",
      target: "step7b",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step7b-step8",
      source: "step7b",
      target: "step8",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    // Row 6
    {
      id: "e-step8-step9",
      source: "step8",
      target: "step9",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step9-step10",
      source: "step9",
      target: "step10",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
    {
      id: "e-step10-step11",
      source: "step10",
      target: "step11",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
    },
  ];
}

const nodeTypes = {
  workflowNode: WorkflowNode,
};

interface WorkflowGraphProps {
  onConfigSave?: (configs: StepConfig[]) => void;
  readOnly?: boolean;
}

export function WorkflowGraph({ onConfigSave: _onConfigSave, readOnly = false }: WorkflowGraphProps) {
  // Fetch models config from backend (source of truth)
  const { stepDefaults, isLoading: _isLoadingConfig, error: _configError } = useModelsConfig();

  // Use backend config if available, fallback to static defaults
  const initialSteps = useMemo(() => {
    if (stepDefaults.length > 0) {
      return stepDefaults.map(convertToStepConfig);
    }
    return FALLBACK_WORKFLOW_STEPS;
  }, [stepDefaults]);

  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(initialSteps);
  const [selectedStep, setSelectedStep] = useState<string | null>(null);

  // Update stepConfigs when backend config is loaded
  useEffect(() => {
    if (stepDefaults.length > 0) {
      setStepConfigs(stepDefaults.map(convertToStepConfig));
    }
  }, [stepDefaults]);

  const handleNodeClick = useCallback((stepId: string) => {
    setSelectedStep(stepId);
  }, []);

  const initialNodes = useMemo(
    () => createInitialNodes(stepConfigs, handleNodeClick),
    [stepConfigs, handleNodeClick],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(createInitialEdges());

  // Update nodes when stepConfigs change (e.g., from backend)
  useEffect(() => {
    const newNodes = createInitialNodes(stepConfigs, handleNodeClick);
    setNodes(newNodes);
  }, [stepConfigs, handleNodeClick, setNodes]);

  const handleConfigChange = useCallback(
    (stepId: string, config: Partial<StepConfig>) => {
      if (readOnly) return;

      setStepConfigs((prev) =>
        prev.map((step) => (step.stepId === stepId ? { ...step, ...config } : step)),
      );

      // Update node data
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === stepId) {
            const nodeData = node.data as WorkflowNodeData;
            return {
              ...node,
              data: {
                ...nodeData,
                aiModel: config.aiModel ?? nodeData.aiModel,
                modelName: config.modelName ?? nodeData.modelName,
              },
            };
          }
          return node;
        }),
      );
    },
    [readOnly, setNodes],
  );

  const handleClose = useCallback(() => {
    setSelectedStep(null);
  }, []);

  const selectedStepConfig = useMemo(
    () => stepConfigs.find((s) => s.stepId === selectedStep) ?? null,
    [stepConfigs, selectedStep],
  );

  return (
    <div className="flex h-full">
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
        </ReactFlow>

        {/* Legend */}
        <div className="absolute top-4 right-4 bg-white rounded-lg border border-gray-200 shadow-sm p-3">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">モデル凡例</h4>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-blue-400" />
              <span className="text-gray-600">Gemini (分析・検索)</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-orange-400" />
              <span className="text-gray-600">Claude (構造・品質)</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded bg-green-400" />
              <span className="text-gray-600">OpenAI</span>
            </div>
          </div>
          <div className="border-t border-gray-200 mt-2 pt-2 space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded-full bg-purple-500" />
              <span className="text-gray-600">並列処理</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="w-3 h-3 rounded-full border-2 border-dashed border-yellow-500" />
              <span className="text-gray-600">承認ポイント</span>
            </div>
          </div>
        </div>
      </div>

      {/* Config Panel */}
      {selectedStep && (
        <NodeConfigPanel
          step={selectedStepConfig}
          onClose={handleClose}
          onConfigChange={handleConfigChange}
        />
      )}
    </div>
  );
}

// Export step configs for use in run creation
// Note: WORKFLOW_STEPS is now fetched from backend via useModelsConfig hook
// FALLBACK_WORKFLOW_STEPS is only used when backend is unavailable
export { FALLBACK_WORKFLOW_STEPS as WORKFLOW_STEPS };
export type { StepConfig };

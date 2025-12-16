import { Node, Edge, MarkerType } from 'reactflow';
import { LLMPlatform } from '@/lib/types';

// ============================================
// Workflow Step Configuration
// ============================================

export type StepAIProvider = 'gemini' | 'claude' | 'manual' | 'gemini+web';

export interface WorkflowStepConfig {
  id: string;
  label: string;
  description: string;
  defaultProvider: StepAIProvider;
  allowedProviders: StepAIProvider[];
  isParallel?: boolean;
  isApprovalPoint?: boolean;
}

// ワークフロー工程の定義
export const WORKFLOW_STEPS: WorkflowStepConfig[] = [
  {
    id: 'step-1',
    label: '入力',
    description: '絶対条件ヒアリング',
    defaultProvider: 'manual',
    allowedProviders: ['manual'],
  },
  {
    id: 'step0',
    label: '準備',
    description: 'キーワード選定',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
  },
  {
    id: 'step1',
    label: '分析',
    description: '競合記事本文取得',
    defaultProvider: 'manual',
    allowedProviders: ['manual'],
  },
  {
    id: 'step2',
    label: '調査',
    description: 'CSV読み込み・検証',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
  },
  {
    id: 'step3a',
    label: '並列A',
    description: 'クエリ分析・ペルソナ',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
    isParallel: true,
  },
  {
    id: 'step3b',
    label: '並列B',
    description: '共起語・関連KW抽出',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
    isParallel: true,
  },
  {
    id: 'step3c',
    label: '並列C',
    description: '競合分析・差別化',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
    isParallel: true,
  },
  {
    id: 'approval',
    label: '承認',
    description: '人間による確認・許可',
    defaultProvider: 'manual',
    allowedProviders: ['manual'],
    isApprovalPoint: true,
  },
  {
    id: 'step4',
    label: '執筆準備',
    description: '戦略的アウトライン',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
  {
    id: 'step5',
    label: '情報収集',
    description: '一次情報収集',
    defaultProvider: 'gemini+web',
    allowedProviders: ['gemini+web'],
  },
  {
    id: 'step6',
    label: '編集',
    description: 'アウトライン強化版',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
  {
    id: 'step6.5',
    label: '統合',
    description: '統合パッケージ化',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
  {
    id: 'step7a',
    label: '初稿',
    description: '本文生成',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
  {
    id: 'step7b',
    label: '推敲',
    description: 'ブラッシュアップ',
    defaultProvider: 'gemini',
    allowedProviders: ['gemini', 'claude'],
  },
  {
    id: 'step8',
    label: '検証',
    description: 'ファクトチェック・FAQ',
    defaultProvider: 'gemini+web',
    allowedProviders: ['gemini+web'],
  },
  {
    id: 'step9',
    label: '最終調整',
    description: '最終リライト',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
  {
    id: 'step10',
    label: '完了',
    description: '最終出力',
    defaultProvider: 'claude',
    allowedProviders: ['claude', 'gemini'],
  },
];

// ============================================
// Node Position Layout
// ============================================

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;
const HORIZONTAL_GAP = 60;
const VERTICAL_GAP = 40;

// ノードの位置を計算
function calculateNodePositions(): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};

  // Row 1: step-1 → step0 → step1 → step2
  positions['step-1'] = { x: 0, y: 150 };
  positions['step0'] = { x: NODE_WIDTH + HORIZONTAL_GAP, y: 150 };
  positions['step1'] = { x: (NODE_WIDTH + HORIZONTAL_GAP) * 2, y: 150 };
  positions['step2'] = { x: (NODE_WIDTH + HORIZONTAL_GAP) * 3, y: 150 };

  // Row 2: Parallel steps (3a, 3b, 3c)
  const parallelStartX = (NODE_WIDTH + HORIZONTAL_GAP) * 4;
  positions['step3a'] = { x: parallelStartX, y: 50 };
  positions['step3b'] = { x: parallelStartX, y: 150 };
  positions['step3c'] = { x: parallelStartX, y: 250 };

  // Approval point
  positions['approval'] = { x: parallelStartX + NODE_WIDTH + HORIZONTAL_GAP, y: 150 };

  // Row 3: step4 → step5 → step6 → step6.5
  const row3StartX = parallelStartX + (NODE_WIDTH + HORIZONTAL_GAP) * 2;
  positions['step4'] = { x: row3StartX, y: 150 };
  positions['step5'] = { x: row3StartX + NODE_WIDTH + HORIZONTAL_GAP, y: 150 };
  positions['step6'] = { x: row3StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 2, y: 150 };
  positions['step6.5'] = { x: row3StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 3, y: 150 };

  // Row 4: step7a → step7b → step8 → step9 → step10
  const row4StartX = row3StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 4;
  positions['step7a'] = { x: row4StartX, y: 150 };
  positions['step7b'] = { x: row4StartX + NODE_WIDTH + HORIZONTAL_GAP, y: 150 };
  positions['step8'] = { x: row4StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 2, y: 150 };
  positions['step9'] = { x: row4StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 3, y: 150 };
  positions['step10'] = { x: row4StartX + (NODE_WIDTH + HORIZONTAL_GAP) * 4, y: 150 };

  return positions;
}

// ============================================
// Generate Nodes and Edges
// ============================================

export function generateWorkflowNodes(
  stepProviders: Record<string, StepAIProvider> = {}
): Node[] {
  const positions = calculateNodePositions();

  return WORKFLOW_STEPS.map((step) => ({
    id: step.id,
    type: 'workflowNode',
    position: positions[step.id] || { x: 0, y: 0 },
    data: {
      label: step.label,
      description: step.description,
      provider: stepProviders[step.id] || step.defaultProvider,
      allowedProviders: step.allowedProviders,
      isParallel: step.isParallel,
      isApprovalPoint: step.isApprovalPoint,
    },
    draggable: false,
  }));
}

export function generateWorkflowEdges(): Edge[] {
  const edgeStyle = {
    strokeWidth: 2,
    stroke: '#6b7280',
  };

  const markerEnd = {
    type: MarkerType.ArrowClosed,
    width: 15,
    height: 15,
    color: '#6b7280',
  };

  return [
    // Linear flow: step-1 → step0 → step1 → step2
    { id: 'e-1-0', source: 'step-1', target: 'step0', style: edgeStyle, markerEnd },
    { id: 'e0-1', source: 'step0', target: 'step1', style: edgeStyle, markerEnd },
    { id: 'e1-2', source: 'step1', target: 'step2', style: edgeStyle, markerEnd },

    // Fork to parallel: step2 → step3a/3b/3c
    { id: 'e2-3a', source: 'step2', target: 'step3a', style: edgeStyle, markerEnd },
    { id: 'e2-3b', source: 'step2', target: 'step3b', style: edgeStyle, markerEnd },
    { id: 'e2-3c', source: 'step2', target: 'step3c', style: edgeStyle, markerEnd },

    // Join from parallel: step3a/3b/3c → approval
    { id: 'e3a-app', source: 'step3a', target: 'approval', style: edgeStyle, markerEnd },
    { id: 'e3b-app', source: 'step3b', target: 'approval', style: edgeStyle, markerEnd },
    { id: 'e3c-app', source: 'step3c', target: 'approval', style: edgeStyle, markerEnd },

    // Continue: approval → step4 → ... → step10
    { id: 'eapp-4', source: 'approval', target: 'step4', style: edgeStyle, markerEnd },
    { id: 'e4-5', source: 'step4', target: 'step5', style: edgeStyle, markerEnd },
    { id: 'e5-6', source: 'step5', target: 'step6', style: edgeStyle, markerEnd },
    { id: 'e6-65', source: 'step6', target: 'step6.5', style: edgeStyle, markerEnd },
    { id: 'e65-7a', source: 'step6.5', target: 'step7a', style: edgeStyle, markerEnd },
    { id: 'e7a-7b', source: 'step7a', target: 'step7b', style: edgeStyle, markerEnd },
    { id: 'e7b-8', source: 'step7b', target: 'step8', style: edgeStyle, markerEnd },
    { id: 'e8-9', source: 'step8', target: 'step9', style: edgeStyle, markerEnd },
    { id: 'e9-10', source: 'step9', target: 'step10', style: edgeStyle, markerEnd },
  ];
}

// ============================================
// Provider Utilities
// ============================================

export function getProviderColor(provider: StepAIProvider): string {
  switch (provider) {
    case 'gemini':
      return 'bg-blue-500';
    case 'claude':
      return 'bg-orange-500';
    case 'gemini+web':
      return 'bg-purple-500';
    case 'manual':
      return 'bg-gray-500';
    default:
      return 'bg-gray-400';
  }
}

export function getProviderLabel(provider: StepAIProvider): string {
  switch (provider) {
    case 'gemini':
      return 'Gemini';
    case 'claude':
      return 'Claude';
    case 'gemini+web':
      return 'Gemini + Web';
    case 'manual':
      return '手動';
    default:
      return provider;
  }
}

export function getProviderIcon(provider: StepAIProvider): string {
  switch (provider) {
    case 'gemini':
      return 'G';
    case 'claude':
      return 'C';
    case 'gemini+web':
      return 'G+';
    case 'manual':
      return 'M';
    default:
      return '?';
  }
}

// Convert StepAIProvider to LLMPlatform for API
export function providerToLLMPlatform(provider: StepAIProvider): LLMPlatform | null {
  switch (provider) {
    case 'gemini':
    case 'gemini+web':
      return 'gemini';
    case 'claude':
      return 'anthropic';
    default:
      return null;
  }
}

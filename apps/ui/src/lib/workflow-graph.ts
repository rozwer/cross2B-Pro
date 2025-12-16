// ============================================
// Workflow Graph Definition for n8n/Dify-like UI
// ============================================

import type { Node, Edge } from 'reactflow';

export type NodeType = 'input' | 'llm' | 'tool' | 'parallel' | 'approval' | 'output';
export type AIProvider = 'gemini' | 'openai' | 'claude' | 'manual' | 'tool';

export interface WorkflowNodeData {
  label: string;
  stepName: string;
  description: string;
  nodeType: NodeType;
  aiProvider: AIProvider;
  outputFile?: string;
  configurable?: boolean;
}

// Node definitions for the SEO article generation workflow
// Layout: Horizontal flow with parallel branch for step3a/3b/3c
export const workflowNodes: Node<WorkflowNodeData>[] = [
  // ============================================
  // Row 1: Semi-Automatic Flow (Human Review)
  // ============================================
  {
    id: 'step-1',
    type: 'workflowNode',
    position: { x: 50, y: 150 },
    data: {
      label: '入力',
      stepName: 'step-1',
      description: '絶対条件ヒアリング',
      nodeType: 'input',
      aiProvider: 'manual',
      outputFile: 'input.json',
    },
  },
  {
    id: 'step0',
    type: 'workflowNode',
    position: { x: 250, y: 150 },
    data: {
      label: '準備',
      stepName: 'step0',
      description: 'キーワード選定',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step0_keyword.json',
      configurable: true,
    },
  },
  {
    id: 'step1',
    type: 'workflowNode',
    position: { x: 450, y: 150 },
    data: {
      label: '分析',
      stepName: 'step1',
      description: '競合記事本文取得',
      nodeType: 'tool',
      aiProvider: 'tool',
      outputFile: 'step1_competitors.csv',
    },
  },
  {
    id: 'step2',
    type: 'workflowNode',
    position: { x: 650, y: 150 },
    data: {
      label: '調査',
      stepName: 'step2',
      description: 'CSV読み込み・検証',
      nodeType: 'llm',
      aiProvider: 'gemini',
      configurable: true,
    },
  },
  // Parallel Processing Nodes (3 parallel branches)
  {
    id: 'step3a',
    type: 'workflowNode',
    position: { x: 850, y: 50 },
    data: {
      label: 'クエリ分析',
      stepName: 'step3a',
      description: 'クエリ分析・ペルソナ',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step3a_query.json',
      configurable: true,
    },
  },
  {
    id: 'step3b',
    type: 'workflowNode',
    position: { x: 850, y: 150 },
    data: {
      label: '共起語抽出',
      stepName: 'step3b',
      description: '共起語・関連KW抽出（心臓部）',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step3b_keywords.json',
      configurable: true,
    },
  },
  {
    id: 'step3c',
    type: 'workflowNode',
    position: { x: 850, y: 250 },
    data: {
      label: '競合分析',
      stepName: 'step3c',
      description: '競合分析・差別化',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step3c_competitor.json',
      configurable: true,
    },
  },
  // Approval Node
  {
    id: 'approval',
    type: 'approvalNode',
    position: { x: 1050, y: 150 },
    data: {
      label: '承認待ち',
      stepName: 'approval',
      description: '人間による確認・許可',
      nodeType: 'approval',
      aiProvider: 'manual',
    },
  },
  // ============================================
  // Row 2: Automatic Flow (after approval)
  // ============================================
  {
    id: 'step4',
    type: 'workflowNode',
    position: { x: 50, y: 400 },
    data: {
      label: '執筆準備',
      stepName: 'step4',
      description: '戦略的アウトライン',
      nodeType: 'llm',
      aiProvider: 'claude',
      outputFile: 'step4_outline.json',
      configurable: true,
    },
  },
  {
    id: 'step5',
    type: 'workflowNode',
    position: { x: 250, y: 400 },
    data: {
      label: '一次情報',
      stepName: 'step5',
      description: '一次情報収集',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step5_sources.json',
      configurable: true,
    },
  },
  {
    id: 'step6',
    type: 'workflowNode',
    position: { x: 450, y: 400 },
    data: {
      label: '編集',
      stepName: 'step6',
      description: 'アウトライン強化版',
      nodeType: 'llm',
      aiProvider: 'claude',
      outputFile: 'step6_enhanced.json',
      configurable: true,
    },
  },
  {
    id: 'step6.5',
    type: 'workflowNode',
    position: { x: 650, y: 400 },
    data: {
      label: '統合',
      stepName: 'step6.5',
      description: '統合パッケージ化',
      nodeType: 'llm',
      aiProvider: 'claude',
      outputFile: 'step6_5_package.md',
      configurable: true,
    },
  },
  {
    id: 'step7a',
    type: 'workflowNode',
    position: { x: 850, y: 400 },
    data: {
      label: '本文生成',
      stepName: 'step7a',
      description: '本文生成 初稿',
      nodeType: 'llm',
      aiProvider: 'claude',
      outputFile: 'step7a_draft.md',
      configurable: true,
    },
  },
  {
    id: 'step7b',
    type: 'workflowNode',
    position: { x: 1050, y: 400 },
    data: {
      label: 'ブラッシュアップ',
      stepName: 'step7b',
      description: 'ブラッシュアップ',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step7b_polished.md',
      configurable: true,
    },
  },
  // ============================================
  // Row 3: Final Steps
  // ============================================
  {
    id: 'step8',
    type: 'workflowNode',
    position: { x: 250, y: 550 },
    data: {
      label: 'ファクトチェック',
      stepName: 'step8',
      description: 'ファクトチェック・FAQ',
      nodeType: 'llm',
      aiProvider: 'gemini',
      outputFile: 'step8_factcheck.json',
      configurable: true,
    },
  },
  {
    id: 'step9',
    type: 'workflowNode',
    position: { x: 450, y: 550 },
    data: {
      label: '最終リライト',
      stepName: 'step9',
      description: '最終リライト',
      nodeType: 'llm',
      aiProvider: 'claude',
      outputFile: 'step9_final.md',
      configurable: true,
    },
  },
  {
    id: 'step10',
    type: 'workflowNode',
    position: { x: 650, y: 550 },
    data: {
      label: '完了',
      stepName: 'step10',
      description: '最終出力',
      nodeType: 'output',
      aiProvider: 'claude',
      outputFile: 'final_article.*',
      configurable: true,
    },
  },
];

// Edge definitions for workflow connections
export const workflowEdges: Edge[] = [
  // Semi-Automatic Flow
  { id: 'e-1-0', source: 'step-1', target: 'step0', animated: true },
  { id: 'e0-1', source: 'step0', target: 'step1' },
  { id: 'e1-2', source: 'step1', target: 'step2' },
  // To parallel nodes (fan-out)
  { id: 'e2-3a', source: 'step2', target: 'step3a' },
  { id: 'e2-3b', source: 'step2', target: 'step3b' },
  { id: 'e2-3c', source: 'step2', target: 'step3c' },
  // From parallel to approval (fan-in)
  { id: 'e3a-app', source: 'step3a', target: 'approval' },
  { id: 'e3b-app', source: 'step3b', target: 'approval' },
  { id: 'e3c-app', source: 'step3c', target: 'approval' },
  // Approval to automatic flow (row transition)
  { id: 'eapp-4', source: 'approval', target: 'step4', label: '承認後', type: 'smoothstep' },
  // Automatic Flow (Row 2)
  { id: 'e4-5', source: 'step4', target: 'step5' },
  { id: 'e5-6', source: 'step5', target: 'step6' },
  { id: 'e6-65', source: 'step6', target: 'step6.5' },
  { id: 'e65-7a', source: 'step6.5', target: 'step7a' },
  { id: 'e7a-7b', source: 'step7a', target: 'step7b' },
  // Row 2 to Row 3 transition
  { id: 'e7b-8', source: 'step7b', target: 'step8', type: 'smoothstep' },
  // Final Steps (Row 3)
  { id: 'e8-9', source: 'step8', target: 'step9' },
  { id: 'e9-10', source: 'step9', target: 'step10' },
];

// Model options per provider
export const modelOptions: Record<AIProvider, { value: string; label: string }[]> = {
  gemini: [
    { value: 'gemini-2.0-flash-exp', label: 'Gemini 2.0 Flash (推奨)' },
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
  ],
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o (推奨)' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'o1-preview', label: 'o1-preview' },
    { value: 'o1-mini', label: 'o1-mini' },
  ],
  claude: [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (推奨)' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  manual: [],
  tool: [],
};

// Get node color based on AI provider
export function getProviderColor(provider: AIProvider): {
  bg: string;
  border: string;
  text: string;
  icon: string;
} {
  switch (provider) {
    case 'gemini':
      return {
        bg: 'bg-blue-50',
        border: 'border-blue-400',
        text: 'text-blue-700',
        icon: '🔷',
      };
    case 'openai':
      return {
        bg: 'bg-emerald-50',
        border: 'border-emerald-400',
        text: 'text-emerald-700',
        icon: '🟢',
      };
    case 'claude':
      return {
        bg: 'bg-orange-50',
        border: 'border-orange-400',
        text: 'text-orange-700',
        icon: '🟠',
      };
    case 'manual':
      return {
        bg: 'bg-gray-50',
        border: 'border-gray-400',
        text: 'text-gray-700',
        icon: '👤',
      };
    case 'tool':
      return {
        bg: 'bg-purple-50',
        border: 'border-purple-400',
        text: 'text-purple-700',
        icon: '🔧',
      };
    default:
      return {
        bg: 'bg-gray-50',
        border: 'border-gray-300',
        text: 'text-gray-600',
        icon: '⚪',
      };
  }
}

// Get node type icon
export function getNodeTypeIcon(nodeType: NodeType): string {
  switch (nodeType) {
    case 'input':
      return '📥';
    case 'llm':
      return '🤖';
    case 'tool':
      return '🔧';
    case 'parallel':
      return '⚡';
    case 'approval':
      return '✋';
    case 'output':
      return '📤';
    default:
      return '⚪';
  }
}

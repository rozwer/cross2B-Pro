'use client';

import { useState, useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type OnNodesChange,
  type OnEdgesChange,
  MarkerType,
  ConnectionLineType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { WorkflowNode } from './WorkflowNode';
import { ApprovalNode } from './ApprovalNode';
import { NodeConfigPanel } from './NodeConfigPanel';
import {
  workflowNodes,
  workflowEdges,
  type WorkflowNodeData,
} from '@/lib/workflow-graph';
import { cn } from '@/lib/utils';
import { Play, Settings, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// Define custom node types
const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode,
  approvalNode: ApprovalNode,
};

// Style edges
const defaultEdgeOptions = {
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 15,
    height: 15,
    color: '#94a3b8',
  },
  style: {
    strokeWidth: 2,
    stroke: '#94a3b8',
  },
};

interface NodeConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  grounding: boolean;
}

interface WorkflowGraphProps {
  onStartRun?: (configs: Record<string, NodeConfig>) => void;
  className?: string;
}

export function WorkflowGraph({ onStartRun, className }: WorkflowGraphProps) {
  // Initialize nodes and edges
  const [nodes, setNodes, onNodesChange] = useNodesState(workflowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    workflowEdges.map((edge) => ({
      ...edge,
      ...defaultEdgeOptions,
    }))
  );

  // Selected node for config panel
  const [selectedNode, setSelectedNode] = useState<{
    id: string;
    data: WorkflowNodeData;
  } | null>(null);

  // Node configurations
  const [nodeConfigs, setNodeConfigs] = useState<Record<string, NodeConfig>>({});

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<WorkflowNodeData>) => {
      if (node.data.configurable) {
        setSelectedNode({ id: node.id, data: node.data });
      }
    },
    []
  );

  // Handle config save
  const onConfigSave = useCallback((nodeId: string, config: NodeConfig) => {
    setNodeConfigs((prev) => ({
      ...prev,
      [nodeId]: config,
    }));
  }, []);

  // Handle start run
  const handleStartRun = useCallback(() => {
    if (onStartRun) {
      onStartRun(nodeConfigs);
    }
  }, [onStartRun, nodeConfigs]);

  // Count configured nodes
  const configuredCount = useMemo(() => Object.keys(nodeConfigs).length, [nodeConfigs]);

  return (
    <div className={cn('relative w-full h-full', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
        className="bg-gradient-to-br from-slate-50 to-slate-100"
      >
        <Background color="#e2e8f0" gap={20} size={1} />

        <Controls
          className="!bg-white !shadow-lg !rounded-lg !border !border-gray-200"
          showInteractive={false}
        />

        <MiniMap
          className="!bg-white !shadow-lg !rounded-lg !border !border-gray-200"
          nodeColor={(node) => {
            const data = node.data as WorkflowNodeData;
            switch (data.aiProvider) {
              case 'gemini':
                return '#3b82f6';
              case 'openai':
                return '#10b981';
              case 'claude':
                return '#f97316';
              case 'manual':
                return '#6b7280';
              case 'tool':
                return '#8b5cf6';
              default:
                return '#9ca3af';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.05)"
        />

        {/* Header Panel */}
        <Panel position="top-left" className="!m-4">
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                <Settings className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-800">
                  ワークフロー設定
                </h2>
                <p className="text-sm text-gray-500">
                  ノードをクリックしてモデルを設定
                </p>
              </div>
            </div>
          </div>
        </Panel>

        {/* Legend Panel */}
        <Panel position="top-right" className="!m-4">
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">凡例</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-gray-600">Gemini</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-gray-600">GPT</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-orange-500" />
                <span className="text-gray-600">Claude</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-500" />
                <span className="text-gray-600">ツール</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-500" />
                <span className="text-gray-600">手動</span>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t mt-2">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-gray-600">承認待ち</span>
              </div>
            </div>
          </div>
        </Panel>

        {/* Action Panel */}
        <Panel position="bottom-center" className="!m-4">
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-3 flex items-center gap-4">
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-blue-600">{configuredCount}</span>
              <span className="text-gray-400"> / {workflowNodes.filter(n => n.data.configurable).length}</span>
              <span className="ml-1">ノード設定済み</span>
            </div>
            <button
              onClick={handleStartRun}
              className={cn(
                'flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-all',
                'bg-gradient-to-r from-green-500 to-emerald-600 text-white',
                'hover:from-green-600 hover:to-emerald-700 hover:shadow-lg',
                'active:scale-95'
              )}
            >
              <Play className="h-4 w-4" />
              実行開始
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {/* Config Panel */}
      {selectedNode && (
        <NodeConfigPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onSave={onConfigSave}
          initialConfig={nodeConfigs[selectedNode.id]}
        />
      )}
    </div>
  );
}

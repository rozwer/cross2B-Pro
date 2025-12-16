'use client';

import { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowNode, WorkflowNodeData } from './WorkflowNode';
import {
  StepAIProvider,
  WORKFLOW_STEPS,
  generateWorkflowNodes,
  generateWorkflowEdges,
  getProviderColor,
  getProviderLabel,
} from './workflowConfig';

// Register custom node types
const nodeTypes = {
  workflowNode: WorkflowNode,
};

export interface WorkflowGraphProps {
  className?: string;
  stepProviders?: Record<string, StepAIProvider>;
  stepStatuses?: Record<string, 'pending' | 'running' | 'completed' | 'failed'>;
  onProviderChange?: (stepId: string, provider: StepAIProvider) => void;
  readOnly?: boolean;
}

export function WorkflowGraph({
  className,
  stepProviders: initialProviders = {},
  stepStatuses = {},
  onProviderChange,
  readOnly = false,
}: WorkflowGraphProps) {
  const [stepProviders, setStepProviders] = useState<Record<string, StepAIProvider>>(
    () => {
      // Initialize with default providers from WORKFLOW_STEPS
      const defaults: Record<string, StepAIProvider> = {};
      WORKFLOW_STEPS.forEach((step) => {
        defaults[step.id] = initialProviders[step.id] || step.defaultProvider;
      });
      return defaults;
    }
  );

  // Generate initial nodes with provider change handlers
  const initialNodes = useMemo(() => {
    const nodes = generateWorkflowNodes(stepProviders);
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        status: stepStatuses[node.id],
        onProviderChange: readOnly
          ? undefined
          : (provider: StepAIProvider) => {
              setStepProviders((prev) => ({
                ...prev,
                [node.id]: provider,
              }));
              onProviderChange?.(node.id, provider);
            },
      },
    }));
  }, [stepProviders, stepStatuses, readOnly, onProviderChange]);

  const initialEdges = useMemo(() => generateWorkflowEdges(), []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when providers or statuses change
  useMemo(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          provider: stepProviders[node.id] || node.data.provider,
          status: stepStatuses[node.id],
          onProviderChange: readOnly
            ? undefined
            : (provider: StepAIProvider) => {
                setStepProviders((prev) => ({
                  ...prev,
                  [node.id]: provider,
                }));
                onProviderChange?.(node.id, provider);
              },
        },
      }))
    );
  }, [stepProviders, stepStatuses, readOnly, onProviderChange, setNodes]);

  // MiniMap node color based on provider
  const getNodeColor = useCallback((node: Node<WorkflowNodeData>) => {
    const provider = node.data?.provider;
    switch (provider) {
      case 'gemini':
        return '#3b82f6'; // blue
      case 'claude':
        return '#f97316'; // orange
      case 'gemini+web':
        return '#8b5cf6'; // purple
      case 'manual':
        return '#6b7280'; // gray
      default:
        return '#9ca3af';
    }
  }, []);

  return (
    <div className={cn('h-full w-full', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{
          padding: 0.2,
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
        minZoom={0.3}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={!readOnly}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e5e7eb" />
        <Controls
          showZoom={false}
          showFitView={false}
          showInteractive={false}
          className="!shadow-none"
        />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="rgba(255, 255, 255, 0.8)"
          className="!bottom-4 !right-4 !h-24 !w-36 !rounded-lg !border !border-gray-200 !bg-white/80 !shadow-md"
        />

        {/* Legend Panel */}
        <Panel position="top-left" className="!m-4">
          <div className="rounded-lg border border-gray-200 bg-white/95 p-3 shadow-md backdrop-blur-sm">
            <h3 className="mb-2 text-xs font-semibold text-gray-700">AIモデル</h3>
            <div className="flex flex-col gap-1.5">
              {(['gemini', 'claude', 'gemini+web', 'manual'] as StepAIProvider[]).map(
                (provider) => (
                  <div key={provider} className="flex items-center gap-2">
                    <span
                      className={cn(
                        'h-3 w-3 rounded-sm',
                        getProviderColor(provider)
                      )}
                    />
                    <span className="text-xs text-gray-600">
                      {getProviderLabel(provider)}
                    </span>
                  </div>
                )
              )}
            </div>
          </div>
        </Panel>

        {/* Parallel & Approval Legend */}
        <Panel position="top-right" className="!m-4">
          <div className="rounded-lg border border-gray-200 bg-white/95 p-3 shadow-md backdrop-blur-sm">
            <h3 className="mb-2 text-xs font-semibold text-gray-700">記号</h3>
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-[8px] font-bold text-white">
                  P
                </span>
                <span className="text-xs text-gray-600">並列処理</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-sm border-2 border-yellow-400 bg-yellow-50" />
                <span className="text-xs text-gray-600">承認待ち</span>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export default WorkflowGraph;

"use client";

import { memo } from "react";
import { Handle, Position, type Node } from "@xyflow/react";
import {
  FileText,
  Search,
  Brain,
  GitBranch,
  CheckCircle,
  Pause,
  Settings,
  Sparkles,
  FileCheck,
  Package,
  FileOutput,
  Image,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface WorkflowNodeData extends Record<string, unknown> {
  stepId: string;
  label: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "waiting";
  isApprovalPoint?: boolean;
  isParallel?: boolean;
  stepType: "input" | "analysis" | "generation" | "verification" | "output" | "approval";
  onNodeClick?: (stepId: string) => void;
}

export type WorkflowNodeType = Node<WorkflowNodeData, "workflowNode">;

interface WorkflowNodeProps {
  data: WorkflowNodeData;
  selected?: boolean;
}

const STEP_ICONS: Record<string, React.ElementType> = {
  "step-1": FileText,
  step0: Settings,
  step1: Search,
  step1_5: Search,
  step2: FileCheck,
  step3a: Brain,
  step3b: Brain,
  step3c: Brain,
  step3_5: Sparkles,
  approval: Pause,
  step4: GitBranch,
  step5: Search,
  step6: Sparkles,
  "step6.5": Package,
  step6_5: Package,
  step7a: FileOutput,
  step7b: FileOutput,
  step8: CheckCircle,
  step9: Sparkles,
  step10: FileOutput,
  step11: Image,
  step12: FileOutput,
};

const STATUS_STYLES: Record<string, string> = {
  pending: "opacity-60",
  running: "ring-2 ring-blue-400 animate-pulse",
  completed: "ring-2 ring-green-400",
  failed: "ring-2 ring-red-400",
  waiting: "ring-2 ring-yellow-400",
};

function WorkflowNodeComponent({ data, selected }: WorkflowNodeProps) {
  const Icon = STEP_ICONS[data.stepId] || Brain;

  const handleClick = () => {
    data.onNodeClick?.(data.stepId);
  };

  return (
    <div
      className={cn(
        "min-w-[180px] rounded-lg border-2 shadow-md transition-all duration-200 cursor-pointer",
        "bg-white border-gray-200",
        STATUS_STYLES[data.status],
        selected && "ring-2 ring-primary-500 ring-offset-2",
        data.isApprovalPoint && "border-dashed border-yellow-500 bg-yellow-50",
      )}
      onClick={handleClick}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />

      {/* Header */}
      <div
        className={cn(
          "px-3 py-2 rounded-t-lg border-b border-gray-200 flex items-center gap-2",
          data.isApprovalPoint ? "bg-yellow-100" : "bg-gray-50",
        )}
      >
        <Icon className="w-4 h-4 text-gray-600" />
        <span className="text-sm font-semibold text-gray-900">{data.label}</span>
        {data.isParallel && (
          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">並列</span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <p className="text-xs text-gray-600 mb-2 line-clamp-2">{data.description}</p>

        {/* Status indicator */}
        <div className="flex items-center gap-1.5">
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              data.status === "pending" && "bg-gray-400",
              data.status === "running" && "bg-blue-500 animate-pulse",
              data.status === "completed" && "bg-green-500",
              data.status === "failed" && "bg-red-500",
              data.status === "waiting" && "bg-yellow-500",
            )}
          />
          <span className="text-xs text-gray-500 capitalize">{data.status}</span>
        </div>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
    </div>
  );
}

export const WorkflowNode = memo(WorkflowNodeComponent);

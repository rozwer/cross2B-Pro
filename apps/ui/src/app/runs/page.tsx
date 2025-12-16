'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { RunList } from '@/components/runs/RunList';
import { WorkflowGraph } from '@/components/workflow';
import { cn } from '@/lib/utils';
import { Workflow, List, Plus } from 'lucide-react';

type TabType = 'workflow' | 'runs';

export default function RunsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('workflow');
  const router = useRouter();

  const handleStartRun = useCallback(
    (configs: Record<string, { model: string; temperature: number; maxTokens: number; grounding: boolean }>) => {
      // Store configs in sessionStorage for the new run page
      sessionStorage.setItem('workflowConfigs', JSON.stringify(configs));
      router.push('/runs/new');
    },
    [router]
  );

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header with Tabs */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SEO記事生成</h1>
          <p className="text-sm text-gray-500 mt-1">
            ワークフローを設定して記事を生成
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-lg">
          <button
            onClick={() => setActiveTab('workflow')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all',
              activeTab === 'workflow'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            <Workflow className="h-4 w-4" />
            ワークフロー
          </button>
          <button
            onClick={() => setActiveTab('runs')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all',
              activeTab === 'runs'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            <List className="h-4 w-4" />
            実行一覧
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 min-h-0">
        {activeTab === 'workflow' ? (
          <div className="h-full rounded-xl border border-gray-200 overflow-hidden bg-white shadow-sm">
            <WorkflowGraph
              onStartRun={handleStartRun}
              className="h-full"
            />
          </div>
        ) : (
          <div className="h-full overflow-auto">
            <RunList />
          </div>
        )}
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { FileText, Code, ImageIcon, File, Download, ChevronDown, ChevronRight } from 'lucide-react';
import type { ArtifactRef, ArtifactContent } from '@/lib/types';
import { api } from '@/lib/api';
import { formatBytes } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { JsonViewer } from './JsonViewer';
import { MarkdownViewer } from './MarkdownViewer';
import { HtmlPreview } from './HtmlPreview';
import { Loading } from '@/components/common/Loading';

interface ArtifactViewerProps {
  runId: string;
  artifacts: ArtifactRef[];
}

export function ArtifactViewer({ runId, artifacts }: ArtifactViewerProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // グループ化
  const groupedArtifacts = artifacts.reduce((acc, artifact) => {
    const stepId = artifact.step_id;
    if (!acc[stepId]) {
      acc[stepId] = [];
    }
    acc[stepId].push(artifact);
    return acc;
  }, {} as Record<string, ArtifactRef[]>);

  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  const loadContent = async (artifact: ArtifactRef) => {
    setSelectedArtifact(artifact);
    setLoading(true);
    try {
      const data = await api.artifacts.download(runId, artifact.id);
      setContent(data);
    } catch (err) {
      console.error('Failed to load artifact content:', err);
      setContent(null);
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (contentType: string) => {
    if (contentType.includes('json')) return <Code className="h-4 w-4" />;
    if (contentType.includes('html')) return <FileText className="h-4 w-4" />;
    if (contentType.includes('markdown')) return <FileText className="h-4 w-4" />;
    if (contentType.includes('image')) return <ImageIcon className="h-4 w-4" />;
    return <File className="h-4 w-4" />;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">成果物</h3>
      </div>

      <div className="flex divide-x divide-gray-200" style={{ minHeight: '300px' }}>
        {/* ファイルリスト */}
        <div className="w-64 flex-shrink-0 overflow-y-auto">
          {Object.entries(groupedArtifacts).map(([stepId, stepArtifacts]) => (
            <div key={stepId}>
              <button
                onClick={() => toggleStep(stepId)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {expandedSteps.has(stepId) ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <span className="font-medium truncate">{stepId}</span>
                <span className="text-xs text-gray-400 ml-auto">
                  {stepArtifacts.length}
                </span>
              </button>

              {expandedSteps.has(stepId) && (
                <div className="pl-4">
                  {stepArtifacts.map((artifact) => (
                    <button
                      key={artifact.id}
                      onClick={() => loadContent(artifact)}
                      className={cn(
                        'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                        selectedArtifact?.id === artifact.id
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-gray-600 hover:bg-gray-50'
                      )}
                    >
                      {getIcon(artifact.content_type)}
                      <div className="flex-1 min-w-0 text-left">
                        <p className="truncate text-xs">
                          {artifact.ref_path.split('/').pop()}
                        </p>
                        <p className="text-xs text-gray-400">
                          {formatBytes(artifact.size_bytes)}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {artifacts.length === 0 && (
            <div className="p-4 text-center text-sm text-gray-500">
              成果物がありません
            </div>
          )}
        </div>

        {/* コンテンツビューア */}
        <div className="flex-1 p-4 overflow-auto">
          {loading ? (
            <Loading text="読み込み中..." />
          ) : selectedArtifact && content ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-900">
                    {selectedArtifact.ref_path}
                  </h4>
                  <p className="text-xs text-gray-500">
                    {selectedArtifact.content_type} | {formatBytes(selectedArtifact.size_bytes)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={`data:${selectedArtifact.content_type};base64,${content.encoding === 'base64' ? content.content : btoa(content.content)}`}
                    download={selectedArtifact.ref_path.split('/').pop()}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    ダウンロード
                  </a>
                </div>
              </div>
              <ContentRenderer
                content={content.content}
                contentType={selectedArtifact.content_type}
                encoding={content.encoding}
              />
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-gray-400">
              ファイルを選択してください
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Markdownコンテンツを含むフィールド名
const MARKDOWN_FIELDS = [
  'draft',
  'polished',
  'final_content',
  'integration_package',
  'markdown',
  'content',
];

function ContentRenderer({
  content,
  contentType,
  encoding,
}: {
  content: string;
  contentType: string;
  encoding: 'utf-8' | 'base64';
}) {
  const [viewMode, setViewMode] = useState<'json' | 'markdown'>('json');
  const decodedContent = encoding === 'base64' ? atob(content) : content;

  // JSONの場合、Markdownフィールドを検出
  if (contentType.includes('json')) {
    let markdownContent: string | null = null;
    let markdownFieldName: string | null = null;

    try {
      const parsed = JSON.parse(decodedContent);
      if (typeof parsed === 'object' && parsed !== null) {
        for (const field of MARKDOWN_FIELDS) {
          if (field in parsed && typeof parsed[field] === 'string' && parsed[field].length > 100) {
            markdownContent = parsed[field];
            markdownFieldName = field;
            break;
          }
        }
      }
    } catch {
      // JSONパースエラーは無視
    }

    // Markdownフィールドが見つかった場合、表示切り替えUI
    if (markdownContent && markdownFieldName) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-3 border-b border-gray-200 pb-2">
            <span className="text-xs text-gray-500">表示モード:</span>
            <button
              onClick={() => setViewMode('json')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                viewMode === 'json'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              JSON
            </button>
            <button
              onClick={() => setViewMode('markdown')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                viewMode === 'markdown'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              {markdownFieldName} (Markdown)
            </button>
          </div>
          {viewMode === 'json' ? (
            <JsonViewer content={decodedContent} />
          ) : (
            <MarkdownViewer content={markdownContent} />
          )}
        </div>
      );
    }

    return <JsonViewer content={decodedContent} />;
  }

  if (contentType.includes('html')) {
    return <HtmlPreview content={decodedContent} />;
  }

  if (contentType.includes('markdown')) {
    return <MarkdownViewer content={decodedContent} />;
  }

  // デフォルト: プレーンテキスト
  return (
    <pre className="p-4 bg-gray-50 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap">
      {decodedContent}
    </pre>
  );
}

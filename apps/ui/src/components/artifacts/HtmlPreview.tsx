'use client';

import { useState } from 'react';
import { Code, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

interface HtmlPreviewProps {
  content: string;
}

export function HtmlPreview({ content }: HtmlPreviewProps) {
  const [mode, setMode] = useState<'preview' | 'source'>('preview');

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setMode('preview')}
          className={cn(
            'inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            mode === 'preview'
              ? 'bg-primary-100 text-primary-700'
              : 'text-gray-600 hover:bg-gray-100'
          )}
        >
          <Eye className="h-3.5 w-3.5" />
          プレビュー
        </button>
        <button
          onClick={() => setMode('source')}
          className={cn(
            'inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            mode === 'source'
              ? 'bg-primary-100 text-primary-700'
              : 'text-gray-600 hover:bg-gray-100'
          )}
        >
          <Code className="h-3.5 w-3.5" />
          ソース
        </button>
      </div>

      {mode === 'preview' ? (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <iframe
            srcDoc={content}
            title="HTML Preview"
            className="w-full h-96 bg-white"
            sandbox="allow-same-origin"
          />
        </div>
      ) : (
        <pre className="p-4 bg-gray-50 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap">
          {content}
        </pre>
      )}
    </div>
  );
}

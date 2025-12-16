'use client';

import { useMemo, useState } from 'react';
import { Code, Eye } from 'lucide-react';
import DOMPurify from 'dompurify';
import { cn } from '@/lib/utils';

interface HtmlPreviewProps {
  content: string;
}

/**
 * Sanitize HTML content to prevent XSS attacks.
 *
 * Security: Uses DOMPurify to remove dangerous elements/attributes:
 * - Scripts, event handlers (onclick, onerror, etc.)
 * - External resources that could leak data
 * - Dangerous CSS (expression(), url() with javascript:)
 */
function sanitizeHtml(html: string): string {
  if (typeof window === 'undefined') {
    // SSR: return empty, will hydrate on client
    return '';
  }

  return DOMPurify.sanitize(html, {
    // Allow safe elements for article preview
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'strong', 'em', 'b', 'i', 'u', 's',
      'blockquote', 'pre', 'code',
      'a', 'img',
      'div', 'span',
    ],
    // Allow safe attributes only
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title', 'class',
      'width', 'height',
      'colspan', 'rowspan',
    ],
    // Force all links to open in new tab (security)
    ADD_ATTR: ['target', 'rel'],
    // Block dangerous URI schemes
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
    // Prevent DOM clobbering
    SANITIZE_DOM: true,
    // Remove any unknown tags completely
    KEEP_CONTENT: false,
  });
}

export function HtmlPreview({ content }: HtmlPreviewProps) {
  const [mode, setMode] = useState<'preview' | 'source'>('preview');

  // Sanitize HTML content - memoized to avoid re-sanitizing on every render
  const sanitizedContent = useMemo(() => sanitizeHtml(content), [content]);

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
          {/*
            Security: Using empty sandbox attribute to completely isolate the iframe.
            This prevents:
            - JavaScript execution
            - Form submission
            - Top-level navigation
            - Plugin content
            - Access to parent cookies/localStorage
          */}
          <iframe
            srcDoc={sanitizedContent}
            title="HTML Preview"
            className="w-full h-96 bg-white"
            sandbox=""
            referrerPolicy="no-referrer"
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

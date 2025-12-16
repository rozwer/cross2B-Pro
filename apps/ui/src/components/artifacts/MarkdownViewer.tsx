'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

interface MarkdownViewerProps {
  content: string;
}

/**
 * Secure Markdown viewer using react-markdown.
 *
 * Security:
 * - react-markdown does NOT use dangerouslySetInnerHTML
 * - All content is parsed and rendered as React components
 * - Links are sanitized (no javascript: or data: URIs)
 * - External links open in new tab with noopener/noreferrer
 */
export function MarkdownViewer({ content }: MarkdownViewerProps) {
  // Custom components for styling and security
  const components: Components = {
    // Security: External links open in new tab with proper rel attributes
    a: ({ href, children, ...props }) => {
      const isExternal = href?.startsWith('http://') || href?.startsWith('https://');
      // Block dangerous URI schemes
      if (href?.startsWith('javascript:') || href?.startsWith('data:')) {
        return <span>{children}</span>;
      }
      return (
        <a
          href={href}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
          className="text-primary-600 hover:underline"
          {...props}
        >
          {children}
        </a>
      );
    },
    // Code blocks with syntax highlighting container
    pre: ({ children, ...props }) => (
      <pre
        className="p-3 bg-gray-800 text-gray-100 rounded-lg text-xs overflow-auto my-2"
        {...props}
      >
        {children}
      </pre>
    ),
    // Inline code
    code: ({ children, className, ...props }) => {
      // Check if this is a code block (has language class) or inline
      const isBlock = className?.includes('language-');
      if (isBlock) {
        return <code className={className} {...props}>{children}</code>;
      }
      return (
        <code className="px-1 py-0.5 bg-gray-100 rounded text-xs font-mono" {...props}>
          {children}
        </code>
      );
    },
    // Headings
    h1: ({ children, ...props }) => (
      <h1 className="text-xl font-bold mt-4 mb-2" {...props}>{children}</h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-lg font-bold mt-3 mb-2" {...props}>{children}</h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-base font-bold mt-2 mb-1" {...props}>{children}</h3>
    ),
    // Lists
    ul: ({ children, ...props }) => (
      <ul className="ml-4 list-disc" {...props}>{children}</ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="ml-4 list-decimal" {...props}>{children}</ol>
    ),
    // Paragraphs
    p: ({ children, ...props }) => (
      <p className="my-1" {...props}>{children}</p>
    ),
    // Images - sanitize src
    img: ({ src, alt, ...props }) => {
      // Only allow https images
      if (src && !src.startsWith('https://')) {
        return <span className="text-gray-400">[Image blocked: insecure source]</span>;
      }
      return <img src={src} alt={alt || ''} className="max-w-full h-auto" {...props} />;
    },
  };

  return (
    <div className="prose prose-sm max-w-none p-4 bg-white rounded-lg">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

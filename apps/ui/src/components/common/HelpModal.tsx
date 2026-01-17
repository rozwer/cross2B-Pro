"use client";

import { useEffect, useRef } from "react";
import { X, Info, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content: string;
  loading?: boolean;
  error?: string | null;
}

export function HelpModal({
  isOpen,
  onClose,
  title,
  content,
  loading = false,
  error = null,
}: HelpModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
      document.body.style.overflow = "hidden";
    } else {
      dialog.close();
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [onClose]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  /**
   * Convert basic markdown to HTML
   * Supports: headers, bold, italic, code blocks, inline code, links, lists
   */
  const renderMarkdown = (markdown: string): string => {
    if (!markdown) return "";
    
    let html = markdown
      // Escape HTML first
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      // Code blocks (must be before other transformations)
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-100 p-3 rounded-lg overflow-x-auto my-3 text-sm"><code>$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1.5 py-0.5 rounded text-sm">$1</code>')
      // Headers
      .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-gray-900 mt-4 mb-2">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-gray-900 mt-4 mb-2">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold text-gray-900 mt-4 mb-2">$1</h1>')
      // Bold and italic
      .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:underline">$1</a>')
      // Unordered lists
      .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
      .replace(/(<li.*<\/li>\n?)+/g, '<ul class="list-disc my-2">$&</ul>')
      // Paragraphs (double newline)
      .replace(/\n\n/g, '</p><p class="my-2">')
      // Single newlines to br
      .replace(/\n/g, '<br />');
    
    // Wrap in paragraph
    html = `<p class="my-2">${html}</p>`;
    
    return html;
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <div className="card w-full max-w-lg shadow-soft-lg animate-scale-in overflow-hidden max-h-[80vh] flex flex-col">
          {/* Header */}
          <div className="flex items-start gap-4 p-5 pb-0 flex-shrink-0">
            {/* Icon */}
            <div className="flex-shrink-0 p-2.5 rounded-xl bg-accent-100">
              <Info className="h-5 w-5 text-accent-600" />
            </div>

            {/* Title */}
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            </div>

            {/* Close button */}
            <button
              onClick={onClose}
              className="flex-shrink-0 p-1.5 -mt-1 -mr-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
              aria-label="閉じる"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-5 pt-4 pb-5 overflow-y-auto flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
                <span className="ml-2 text-gray-500">読み込み中...</span>
              </div>
            ) : error ? (
              <div className="text-error-600 bg-error-50 p-4 rounded-lg">
                {error}
              </div>
            ) : (
              <div
                className="prose prose-sm max-w-none text-gray-600 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end p-5 pt-0 flex-shrink-0">
            <button onClick={onClose} className="btn btn-secondary">
              閉じる
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}

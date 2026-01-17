"use client";

import { useState, useCallback } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { HelpModal } from "./HelpModal";

interface HelpButtonProps {
  helpKey: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

interface HelpContent {
  id: number;
  help_key: string;
  title: string;
  content: string;
  category: string | null;
  display_order: number;
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
};

const buttonSizeClasses = {
  sm: "p-0.5",
  md: "p-1",
  lg: "p-1.5",
};

export function HelpButton({ helpKey, className, size = "md" }: HelpButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [helpContent, setHelpContent] = useState<HelpContent | null>(null);

  const fetchHelpContent = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/help/${encodeURIComponent(helpKey)}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("ヘルプコンテンツが見つかりません");
        }
        throw new Error("ヘルプの取得に失敗しました");
      }

      const data: HelpContent = await response.json();
      setHelpContent(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  }, [helpKey]);

  const handleClick = useCallback(() => {
    setIsOpen(true);
    if (!helpContent) {
      fetchHelpContent();
    }
  }, [helpContent, fetchHelpContent]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className={cn(
          "inline-flex items-center justify-center",
          "text-gray-400 hover:text-gray-600",
          "hover:bg-gray-100 rounded-full",
          "transition-all duration-150",
          "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1",
          buttonSizeClasses[size],
          className
        )}
        aria-label="ヘルプを表示"
        title="ヘルプ"
      >
        <HelpCircle className={sizeClasses[size]} />
      </button>

      <HelpModal
        isOpen={isOpen}
        onClose={handleClose}
        title={helpContent?.title || "ヘルプ"}
        content={helpContent?.content || ""}
        loading={loading}
        error={error}
      />
    </>
  );
}

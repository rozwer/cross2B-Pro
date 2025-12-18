"use client";

import { useEffect, useRef } from "react";
import { X, AlertTriangle, CheckCircle, Info, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "default" | "danger" | "success" | "info";
  loading?: boolean;
  children?: React.ReactNode;
}

const variantConfig = {
  default: {
    icon: null,
    iconBg: "bg-primary-100",
    iconColor: "text-primary-600",
    confirmBtn: "btn btn-primary",
  },
  danger: {
    icon: AlertTriangle,
    iconBg: "bg-error-100",
    iconColor: "text-error-600",
    confirmBtn: "btn btn-danger",
  },
  success: {
    icon: CheckCircle,
    iconBg: "bg-success-100",
    iconColor: "text-success-600",
    confirmBtn: "btn btn-primary",
  },
  info: {
    icon: Info,
    iconBg: "bg-accent-100",
    iconColor: "text-accent-600",
    confirmBtn: "btn btn-primary",
  },
};

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = "確認",
  cancelText = "キャンセル",
  variant = "default",
  loading = false,
  children,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const config = variantConfig[variant];
  const IconComponent = config.icon;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
      // Prevent body scroll
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

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <div className="card w-full max-w-md shadow-soft-lg animate-scale-in overflow-hidden">
          {/* Header */}
          <div className="flex items-start gap-4 p-5 pb-0">
            {/* Icon */}
            {IconComponent && (
              <div className={cn("flex-shrink-0 p-2.5 rounded-xl", config.iconBg)}>
                <IconComponent className={cn("h-5 w-5", config.iconColor)} />
              </div>
            )}

            {/* Title & Description */}
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
              <p className="mt-1 text-sm text-gray-500 leading-relaxed">{description}</p>
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
          {children && <div className="px-5 pt-4">{children}</div>}

          {/* Footer */}
          <div className="flex justify-end gap-3 p-5 pt-6">
            <button onClick={onClose} disabled={loading} className="btn btn-secondary">
              {cancelText}
            </button>
            {confirmText && (
              <button
                onClick={onConfirm}
                disabled={loading}
                className={cn(config.confirmBtn, "min-w-[100px]")}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    処理中...
                  </>
                ) : (
                  confirmText
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}

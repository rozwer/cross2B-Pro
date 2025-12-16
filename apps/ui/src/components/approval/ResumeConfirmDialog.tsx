'use client';

import { useState } from 'react';
import { Play, AlertTriangle } from 'lucide-react';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

interface ResumeConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  stepName: string;
  stepLabel: string;
}

export function ResumeConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  stepName,
  stepLabel,
}: ResumeConfirmDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      onClose={onClose}
      onConfirm={handleConfirm}
      title="部分再実行の確認"
      description={`${stepLabel} から再実行します。`}
      confirmText="再実行開始"
      cancelText="キャンセル"
      loading={loading}
    >
      <div className="mt-4 space-y-3">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">注意事項</p>
              <ul className="mt-1 space-y-1 list-disc list-inside text-amber-700">
                <li>新しい Run が作成されます</li>
                <li>このステップより前の成果物は引き継がれます</li>
                <li>元の Run は「再実行済み」としてマークされます</li>
              </ul>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </div>
    </ConfirmDialog>
  );
}

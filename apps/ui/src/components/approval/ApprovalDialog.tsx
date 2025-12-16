'use client';

import { useState } from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

interface ApprovalDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  runId: string;
}

export function ApprovalDialog({
  isOpen,
  onClose,
  onApprove,
  onReject,
  runId,
}: ApprovalDialogProps) {
  const [mode, setMode] = useState<'select' | 'approve' | 'reject'>('select');
  const [rejectReason, setRejectReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setLoading(true);
    setError(null);
    try {
      await onApprove();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setError('却下理由は必須です');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await onReject(rejectReason);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setMode('select');
    setRejectReason('');
    setError(null);
    onClose();
  };

  if (mode === 'select') {
    return (
      <ConfirmDialog
        isOpen={isOpen}
        onClose={handleClose}
        onConfirm={() => {}}
        title="承認確認"
        description="このRunの承認処理を選択してください"
        confirmText=""
        cancelText="キャンセル"
      >
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setMode('approve')}
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            <CheckCircle className="h-5 w-5" />
            承認
          </button>
          <button
            onClick={() => setMode('reject')}
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            <XCircle className="h-5 w-5" />
            却下
          </button>
        </div>
      </ConfirmDialog>
    );
  }

  if (mode === 'approve') {
    return (
      <ConfirmDialog
        isOpen={isOpen}
        onClose={handleClose}
        onConfirm={handleApprove}
        title="承認の確認"
        description="このRunを承認して後続の工程を開始しますか？"
        confirmText="承認する"
        cancelText="戻る"
        loading={loading}
      >
        {error && (
          <p className="text-sm text-red-600 mt-2">{error}</p>
        )}
      </ConfirmDialog>
    );
  }

  return (
    <ConfirmDialog
      isOpen={isOpen}
      onClose={handleClose}
      onConfirm={handleReject}
      title="却下の確認"
      description="このRunを却下します。却下理由を入力してください。"
      confirmText="却下する"
      cancelText="戻る"
      variant="danger"
      loading={loading}
    >
      <div className="mt-2">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          却下理由 <span className="text-red-500">*</span>
        </label>
        <textarea
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
          placeholder="却下の理由を入力してください"
        />
        {error && (
          <p className="text-sm text-red-600 mt-2">{error}</p>
        )}
      </div>
    </ConfirmDialog>
  );
}

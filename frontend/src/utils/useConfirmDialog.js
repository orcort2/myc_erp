import { useState } from 'react';

function useConfirmDialog() {
  const [dialog, setDialog] = useState(null);

  function openConfirm(config) {
    setDialog({
      cancelText: 'Cancelar',
      confirmText: 'Confirmar',
      isConfirming: false,
      variant: 'normal',
      ...config
    });
  }

  function closeConfirm() {
    setDialog((current) => {
      if (current?.isConfirming) {
        return current;
      }
      return null;
    });
  }

  async function handleConfirm() {
    if (!dialog?.onConfirm) {
      setDialog(null);
      return;
    }

    setDialog((current) => (current ? { ...current, isConfirming: true } : current));
    try {
      await dialog.onConfirm();
    } finally {
      setDialog(null);
    }
  }

  return {
    closeConfirm,
    confirmDialog: dialog,
    handleConfirm,
    openConfirm
  };
}

export default useConfirmDialog;

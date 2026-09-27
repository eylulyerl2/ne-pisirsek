import { useState, type ReactNode } from "react";

interface ConfirmButtonProps {
  children: ReactNode;
  confirmText: string;
  confirmLabel?: string;
  onConfirm: () => void;
  disabled?: boolean;
  className?: string;
}

/** Geri alınamayan işlemler için iki adımlı onay: önce düğme, sonra "Emin misiniz?". */
export function ConfirmButton({ children, confirmText, confirmLabel = "Evet", onConfirm, disabled, className = "btn btn-sm btn-danger" }: ConfirmButtonProps) {
  const [asking, setAsking] = useState(false);

  if (!asking) {
    return (
      <button type="button" className={className} disabled={disabled} onClick={() => setAsking(true)}>
        {children}
      </button>
    );
  }
  return (
    <span className="confirm-row" role="group" aria-label="Onay">
      <span className="small">{confirmText}</span>
      <button
        type="button"
        className="btn btn-sm btn-danger"
        disabled={disabled}
        onClick={() => {
          setAsking(false);
          onConfirm();
        }}
      >
        {confirmLabel}
      </button>
      <button type="button" className="btn btn-sm" onClick={() => setAsking(false)}>
        Vazgeç
      </button>
    </span>
  );
}

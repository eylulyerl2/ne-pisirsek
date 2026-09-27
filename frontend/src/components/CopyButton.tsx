import { useState } from "react";

interface CopyButtonProps {
  text: string;
  label: string;
  copiedLabel?: string;
  primary?: boolean;
}

export function CopyButton({ text, label, copiedLabel = "Kopyalandı ✓", primary = false }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      window.prompt("Kopyalayın:", text);
    }
  }

  return (
    <button type="button" className={`btn btn-sm${primary ? " btn-primary" : ""}`} onClick={copy}>
      {copied ? copiedLabel : label}
    </button>
  );
}

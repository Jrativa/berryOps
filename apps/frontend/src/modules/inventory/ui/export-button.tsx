import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Download } from "lucide-react";

import { Button } from "@/shared/ui/button";

interface Props {
  onExport: () => Promise<void>;
  label?: string;
}

/** Botón de descarga con estado de carga y mensaje de error propio. */
export function ExportButton({ onExport, label }: Props) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const run = async () => {
    setBusy(true);
    setFailed(false);
    try {
      await onExport();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-3">
      <Button variant="secondary" size="sm" loading={busy} onClick={run}>
        <Download />
        {label ?? t("inventory.export")}
      </Button>
      <span aria-live="polite">{failed && <span className="text-sm text-danger">{t("inventory.export.error")}</span>}</span>
    </span>
  );
}

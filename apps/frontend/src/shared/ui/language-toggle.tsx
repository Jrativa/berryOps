import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";

import { toggleLanguage } from "@/i18n/config";
import { Button } from "@/shared/ui/button";

export function LanguageToggle({ className }: { className?: string }) {
  const { t, i18n } = useTranslation();

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={className}
      onClick={toggleLanguage}
      aria-label={t("lang.switch")}
    >
      <Languages />
      {i18n.language === "en" ? "ES" : "EN"}
    </Button>
  );
}

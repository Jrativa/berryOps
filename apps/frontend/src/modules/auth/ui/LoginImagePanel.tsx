import { useTranslation } from "react-i18next";
import { motion } from "motion/react";
import { Cherry } from "lucide-react";

import { spring } from "@/shared/lib/motion";

export default function LoginImagePanel() {
  const { t } = useTranslation();

  return (
    <div className="relative hidden lg:block lg:h-dvh overflow-hidden bg-midnight">
      <img
        src="/images/blueberry-field.jpg"
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-midnight/80 via-midnight/20 to-midnight/10" />

      {/* Material translúcido sobre la imagen: la foto sigue presente debajo */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring, delay: 0.15 }}
        className="glass-dark absolute inset-x-8 bottom-8 rounded-card p-8 text-cream"
      >
        <Cherry className="mb-5 size-9 opacity-90" strokeWidth={1.5} aria-hidden />
        <h2 className="text-4xl font-semibold text-balance">{t("app.tagline")}</h2>
        <p className="mt-2 text-lg font-medium text-cream/80">{t("app.subtagline")}</p>
      </motion.div>
    </div>
  );
}

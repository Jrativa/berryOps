import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { motion } from "motion/react";
import { Cherry } from "lucide-react";

import { useAuthStore } from "@/modules/auth/application/authStore";
import { LanguageToggle } from "@/shared/ui/language-toggle";
import { spring } from "@/shared/lib/motion";
import { LoginForm } from "./LoginForm";
import LoginImagePanel from "./LoginImagePanel";

export default function LoginPage() {
  const { t } = useTranslation();
  const { login, isLoading, error, user } = useAuthStore();

  if (user) return <Navigate to="/home" replace />;

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <LoginImagePanel />

      <main className="relative flex items-center justify-center px-6 py-16">
        <LanguageToggle className="absolute right-4 top-4" />

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={spring}
          className="w-full max-w-sm"
        >
          <div className="mb-10 flex flex-col items-center text-center lg:items-start lg:text-left">
            <div className="mb-6 grid size-14 place-items-center rounded-2xl bg-midnight text-cream">
              <Cherry className="size-7" strokeWidth={1.5} aria-hidden />
            </div>
            <h1 className="text-4xl font-semibold">{t("auth.welcome")}</h1>
            <p className="mt-2 text-base text-dusty">{t("auth.subtitle")}</p>
          </div>

          <LoginForm isLoading={isLoading} error={error} onSubmit={login} />

          <p className="mt-8 text-center text-sm text-dusty lg:text-left">{t("auth.noaccount")}</p>
        </motion.div>
      </main>
    </div>
  );
}

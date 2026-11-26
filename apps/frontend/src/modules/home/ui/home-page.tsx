import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { ArrowUpRight, Boxes, Receipt, ShoppingBasket, UsersRound, type LucideIcon } from "lucide-react";

import { useAuthStore } from "@/modules/auth/application/authStore";
import { riseIn, stagger } from "@/shared/lib/motion";
import { Navbar } from "./navbar";

const ADMIN_ROLES = ["admin", "administrador"];

interface ModuleItem {
  key: string;
  icon: LucideIcon;
  adminOnly?: boolean;
  href?: string; // si existe, el módulo ya está disponible
}

// Los módulos sin `href` aún no existen: se muestran como "próximamente", sin enlaces falsos.
const MODULES: ModuleItem[] = [
  { key: "inventory", icon: Boxes, href: "/inventory" },
  { key: "sales", icon: ShoppingBasket },
  { key: "expenses", icon: Receipt },
  { key: "users", icon: UsersRound, adminOnly: true },
];

function greetingKey() {
  const hour = new Date().getHours();
  if (hour < 12) return "home.greeting.morning";
  if (hour < 20) return "home.greeting.afternoon";
  return "home.greeting.evening";
}

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const isAdmin = !!user && ADMIN_ROLES.includes(user.role.toLowerCase());
  const modules = MODULES.filter((m) => !m.adminOnly || isAdmin);

  return (
    <div className="min-h-dvh">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 pb-20 pt-24">
        <motion.div variants={stagger} initial="hidden" animate="show">
          {/* Cabecera: la foto sigue visible bajo un material translúcido */}
          <motion.section
            variants={riseIn}
            className="relative isolate overflow-hidden rounded-card bg-midnight"
          >
            <img
              src="/images/blueberry-field.jpg"
              alt=""
              className="absolute inset-0 -z-10 h-full w-full object-cover"
            />
            <div className="absolute inset-0 -z-10 bg-gradient-to-t from-midnight/85 via-midnight/30 to-transparent" />
            <div className="flex min-h-72 flex-col justify-end p-8 text-cream sm:min-h-80 sm:p-10">
              <p className="text-sm font-medium text-cream/75">{t("app.tagline")}</p>
              <h1 className="mt-2 text-4xl font-semibold sm:text-5xl">
                {t(greetingKey())}, {user?.username}
              </h1>
              <p className="mt-3 text-lg text-cream/80">{t("app.subtagline")}</p>
            </div>
          </motion.section>

          <motion.div variants={riseIn} className="mb-6 mt-14">
            <h2 className="text-3xl font-semibold">{t("home.modules")}</h2>
            <p className="mt-1.5 text-base text-dusty">{t("home.modules.subtitle")}</p>
          </motion.div>

          <ul className="grid gap-4 sm:grid-cols-2">
            {modules.map(({ key, icon: Icon, href }) => (
              <motion.li key={key} variants={riseIn}>
                {(() => {
                  const body = (
                    <>
                      <div className="flex items-start justify-between">
                        <div className="grid size-11 place-items-center rounded-control bg-purple/10 text-purple">
                          <Icon className="size-5" strokeWidth={1.75} aria-hidden />
                        </div>
                        {href ? (
                          <ArrowUpRight className="size-5 text-dusty" aria-hidden />
                        ) : (
                          <span className="rounded-full bg-midnight/[0.06] px-2.5 py-1 text-xs font-medium text-dusty">
                            {t("home.soon")}
                          </span>
                        )}
                      </div>
                      <h3 className="mt-5 text-xl font-semibold">{t(`home.module.${key}.title`)}</h3>
                      <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-dusty">
                        {t(`home.module.${key}.desc`)}
                      </p>
                    </>
                  );
                  const base = "block h-full rounded-card border border-hairline bg-surface p-6";
                  return href ? (
                    <motion.div whileTap={{ scale: 0.98 }} transition={{ type: "spring", bounce: 0, duration: 0.25 }} className="h-full">
                      <Link to={href} className={`${base} transition-colors hover:bg-midnight/[0.02]`}>
                        {body}
                      </Link>
                    </motion.div>
                  ) : (
                    <div className={base}>{body}</div>
                  );
                })()}
              </motion.li>
            ))}
          </ul>
        </motion.div>
      </main>

      <footer className="pb-10 text-center text-xs text-dusty">{t("home.footer")}</footer>
    </div>
  );
}

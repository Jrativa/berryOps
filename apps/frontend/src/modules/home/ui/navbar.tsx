import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Cherry, LogOut } from "lucide-react";

import { useAuthStore } from "@/modules/auth/application/authStore";
import { Button } from "@/shared/ui/button";
import { LanguageToggle } from "@/shared/ui/language-toggle";
import { cn } from "@/shared/lib/utils";

export function Navbar() {
  const { t } = useTranslation();
  const { user, logout } = useAuthStore();
  const [scrolled, setScrolled] = useState(false);

  // Efecto de borde de scroll: el divisor aparece solo cuando el contenido pasa por debajo
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "glass fixed inset-x-0 top-0 z-50 border-b transition-[border-color] duration-200",
        scrolled ? "border-hairline" : "border-transparent",
      )}
    >
      <nav className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-2.5">
          <div className="grid size-8 place-items-center rounded-[10px] bg-midnight text-cream">
            <Cherry className="size-[18px]" strokeWidth={1.75} aria-hidden />
          </div>
          <span className="hidden text-[0.9375rem] font-semibold tracking-tight sm:inline">{t("app.name")}</span>
        </div>

        <div className="flex items-center gap-1" role="navigation" aria-label={t("app.name")}>
          {[
            { to: "/home", label: t("nav.home") },
            { to: "/inventory", label: t("nav.inventory") },
          ].map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors",
                  isActive ? "bg-midnight/[0.08] text-midnight" : "text-dusty hover:text-midnight",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <LanguageToggle />
          {user && (
            <>
              <div
                className="mx-1 hidden items-center gap-2 sm:flex"
                aria-label={`${user.username}, ${user.role}`}
              >
                <div className="grid size-8 place-items-center rounded-full bg-purple text-xs font-semibold text-cream">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div className="text-xs leading-tight">
                  <p className="font-medium">{user.username}</p>
                  <p className="text-dusty">{user.role}</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={logout} aria-label={t("auth.signout")}>
                <LogOut />
                <span className="hidden sm:inline">{t("auth.signout")}</span>
              </Button>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

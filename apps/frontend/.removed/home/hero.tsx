import { ArrowRight, Play } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/badge";

import { useAuthStore } from "@/modules/auth/application/authStore";

export function Hero() {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const handleScrollToFeatures = () => {
    const element = document.getElementById("features");
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-dusty/5 to-transparent pointer-events-none" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-4xl mx-auto">
          <Badge
            variant="outline"
            className="mb-6 px-4 py-1.5 text-sm font-medium bg-cream border-midnight/10 text-midnight/80 hover:bg-midnight/5 cursor-pointer transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-purple mr-2 inline-block animate-pulse" />
            {t("auth.welcome")}, {user?.username ?? "User"}
          </Badge>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-midnight tracking-tight text-balance">
            {t("app.name")}
            <br />
            <span className="text-dusty">{t("app.tagline")}</span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-midnight/60 max-w-2xl mx-auto text-pretty leading-relaxed">
            {t("app.subtagline")}
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              className="bg-midnight hover:bg-midnight/90 text-cream px-8 h-12 text-base"
              onClick={handleScrollToFeatures}
            >
              Ver Funcionalidades
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>

        <div className="mt-16 lg:mt-20">
          <div className="relative max-w-4xl mx-auto aspect-video rounded-2xl overflow-hidden shadow-2xl shadow-midnight/10 border border-midnight/10 bg-midnight/5 group cursor-pointer">
            <div className="absolute inset-0 bg-midnight/30 flex items-center justify-center group-hover:bg-midnight/40 transition-colors z-10">
              <div className="size-16 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                <Play className="size-7 text-midnight ml-0.5" fill="currentColor" />
              </div>
            </div>
            <img
              src="https://images.unsplash.com/photo-1595853035070-59a39fe84de3?w=1200&q=80"
              alt="Video tutorial"
              className="w-full h-full object-cover"
            />
          </div>
          <p className="text-center text-sm text-midnight/40 mt-4">
            Mira el tutorial para comenzar con {t("app.name")}
          </p>
        </div>
      </div>
    </section>
  );
}

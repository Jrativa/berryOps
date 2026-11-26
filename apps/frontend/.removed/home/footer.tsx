import { useTranslation } from "react-i18next";
import { Cherry, Mail, Phone, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

const footerLinks = {
  producto: [
    { label: "Funcionalidades", href: "#features" },
    { label: "Dashboard", href: "#" },
  ],
  empresa: [
    { label: "Nosotros", href: "#about" },
    { label: "Historia", href: "#" },
  ],
  soporte: [
    { label: "Ayuda", href: "#" },
    { label: "Contacto", href: "#contact" },
  ],
};

export function Footer() {
  const { t } = useTranslation();

  const handleSmoothScroll = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const targetId = href.replace("#", "");
      const element = document.getElementById(targetId);
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <footer id="contact" className="bg-midnight/[0.02] border-t border-midnight/5">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12">
          <div className="col-span-2">
            <Link to="/" className="flex items-center gap-2 mb-4">
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-midnight text-cream">
                <Cherry className="w-5 h-5" />
              </div>
              <span className="font-semibold text-midnight text-lg tracking-tight">
                {t("app.name")}
              </span>
            </Link>
            <p className="text-sm text-midnight/60 max-w-xs leading-relaxed mb-6">
              Sistema de gestion de inventario agricola creado con amor
              por una familia para familias agricultoras.
            </p>

            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-midnight/60">
                <Mail className="w-4 h-4" />
                <span>contacto@blueberryledger.com</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-midnight/60">
                <Phone className="w-4 h-4" />
                <span>+1 (555) 123-4567</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-midnight/60">
                <MapPin className="w-4 h-4" />
                <span>Valle Central, California</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-midnight text-sm mb-4">Producto</h3>
            <ul className="space-y-3">
              {footerLinks.producto.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    onClick={(e) => handleSmoothScroll(e, link.href)}
                    className="text-sm text-midnight/60 hover:text-midnight transition-colors cursor-pointer"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-midnight text-sm mb-4">Empresa</h3>
            <ul className="space-y-3">
              {footerLinks.empresa.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    onClick={(e) => handleSmoothScroll(e, link.href)}
                    className="text-sm text-midnight/60 hover:text-midnight transition-colors cursor-pointer"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-midnight text-sm mb-4">Soporte</h3>
            <ul className="space-y-3">
              {footerLinks.soporte.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    onClick={(e) => handleSmoothScroll(e, link.href)}
                    className="text-sm text-midnight/60 hover:text-midnight transition-colors cursor-pointer"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-midnight/5 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-sm text-midnight/50">
            {new Date().getFullYear()} {t("app.name")}. Hecho con amor en familia.
          </p>
        </div>
      </div>
    </footer>
  );
}

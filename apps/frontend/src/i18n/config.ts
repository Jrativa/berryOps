import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import es from "./locales/es.json";

function initialLanguage(): "en" | "es" {
  const saved = localStorage.getItem("language");
  if (saved === "en" || saved === "es") return saved;
  return navigator.language?.toLowerCase().startsWith("es") ? "es" : "en";
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
  },
  lng: initialLanguage(),
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

// Mantiene el atributo lang del documento sincronizado (lectores de pantalla, traducción del navegador)
document.documentElement.lang = i18n.language;
i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

export function toggleLanguage() {
  const next = i18n.language === "en" ? "es" : "en";
  i18n.changeLanguage(next);
  localStorage.setItem("language", next);
}

export default i18n;

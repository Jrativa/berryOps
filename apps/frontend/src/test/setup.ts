import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import i18n from "@/i18n/config";

i18n.changeLanguage("es");

// jsdom no implementa scrollIntoView
Element.prototype.scrollIntoView = () => {};

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

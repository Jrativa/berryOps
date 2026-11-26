import i18n from "@/i18n/config";

export function formatNumber(value: number, maxDecimals = 1): string {
  return new Intl.NumberFormat(i18n.language, { maximumFractionDigits: maxDecimals }).format(value);
}

export function formatKg(value: number): string {
  return `${formatNumber(value)} kg`;
}

/** "2026-03-05" → fecha local sin desfase de zona horaria (se interpreta como día, no como instante). */
export function parseDay(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDay(day: string, opts: Intl.DateTimeFormatOptions = { dateStyle: "medium" }): string {
  return new Intl.DateTimeFormat(i18n.language, opts).format(parseDay(day));
}

export function formatMonth(month: string, style: "short" | "long" = "short"): string {
  return new Intl.DateTimeFormat(i18n.language, { month: style, year: style === "long" ? "numeric" : undefined }).format(
    parseDay(`${month}-01`),
  );
}

export function todayISO(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

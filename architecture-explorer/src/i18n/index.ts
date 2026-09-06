import en from "../../content/locales/en.json";
import ko from "../../content/locales/ko-KR.json";
export type Language = "en" | "ko-KR";
export function language(): Language {
  return location.hash.startsWith("#/en/") || location.hash === "#/en"
    ? "en"
    : location.hash.startsWith("#/ko-KR")
      ? "ko-KR"
      : localStorage.getItem("architecture-language") === "en"
        ? "en"
        : navigator.language.startsWith("ko")
          ? "ko-KR"
          : "en";
}
export function t(key: string): string {
  return (
    ((language() === "en" ? en : ko) as Record<string, string>)[key] || key
  );
}
export const route = (lang: Language, path = "") =>
  `#/${lang}${path ? "/" + path : ""}`;

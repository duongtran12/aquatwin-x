import { createContext, useContext, useEffect, useState } from "react";
import { LANGUAGE_STORAGE_KEY, LOCALES, readLanguage, translate } from "./translations";

export { localizeStatus, runtimeLabel, valveActionLabel } from "./translations";

const LanguageContext = createContext(null);
const descriptions = {
  vi: "AquaTwin-X hỗ trợ mô phỏng sự cố và phục hồi mạng cấp nước.",
  en: "AquaTwin-X water network recovery dashboard.",
};

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => readLanguage(() => window.localStorage));

  useEffect(() => {
    document.documentElement.lang = language;
    document.querySelector('meta[name="description"]')?.setAttribute("content", descriptions[language]);
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // The selector still works for this page when browser storage is unavailable.
    }
  }, [language]);

  const t = (message, values) => translate(language, message, values);
  return <LanguageContext.Provider value={{ language, setLanguage, locale: LOCALES[language], t }}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}

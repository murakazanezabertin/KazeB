import { createContext, useContext, useCallback, useState, type ReactNode } from "react";

import { getCsrfToken, getHomepage, type HomepageData } from "./api/client";

type LanguageContextType = {
  language: HomepageData["language"];
  labels: HomepageData["labels"];
  setLanguage: (language: HomepageData["language"]) => Promise<void>;
  setPageLabels: (language: HomepageData["language"], labels: HomepageData["labels"]) => void;
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({
  children,
  initialLanguage,
  initialLabels,
}: {
  children: ReactNode;
  initialLanguage: HomepageData["language"];
  initialLabels: HomepageData["labels"];
}) {
  const [language, setLanguageState] = useState<HomepageData["language"]>(initialLanguage);
  const [labels, setLabels] = useState<HomepageData["labels"]>(initialLabels);

  const setLanguage = useCallback(
    async (nextLanguage: HomepageData["language"]) => {
      const token = await getCsrfToken();
      const body = new URLSearchParams();
      body.set("language", nextLanguage);
      body.set("csrfmiddlewaretoken", token);
      const djangoUrl = window.location.origin.replace(/:5173$/, ":8000");
      const response = await fetch(`${djangoUrl}/i18n/setlang/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": token,
        },
        credentials: "include",
        body,
      });
      if (!response.ok) {
        throw new Error(`Language change failed (${response.status}).`);
      }
      const data = await getHomepage();
      setLanguageState(data.language);
      setLabels(data.labels);
      document.documentElement.lang = data.language;
    },
    [],
  );

  const setPageLabels = useCallback(
    (nextLanguage: HomepageData["language"], nextLabels: HomepageData["labels"]) => {
      setLanguageState(nextLanguage);
      setLabels(nextLabels);
      document.documentElement.lang = nextLanguage;
    },
    [],
  );

  const value: LanguageContextType = {
    language,
    labels,
    setLanguage,
    setPageLabels,
  };

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}

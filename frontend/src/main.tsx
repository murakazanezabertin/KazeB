import { StrictMode } from "react";
import ReactDOM from "react-dom/client";

import { LanguageProvider } from "./LanguageContext";
import type { HomepageData } from "./api/client";
import "../../static/vendor/bootstrap/bootstrap.min.css";
import "../../static/css/style.css";
import "./marketplace.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LanguageProvider
      initialLanguage="rw"
      initialLabels={{} as HomepageData["labels"]}
    >
      <App />
    </LanguageProvider>
  </StrictMode>,
);

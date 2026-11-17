import { StrictMode } from "react";
import ReactDOM from "react-dom/client";

import "../../static/vendor/bootstrap/bootstrap.min.css";
import "../../static/css/style.css";
import "./marketplace.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

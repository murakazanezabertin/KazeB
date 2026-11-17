import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const djangoUrl = env.DJANGO_URL || "http://127.0.0.1:8000";
  const proxyConfig: ProxyOptions = {
    target: djangoUrl,
  };
  const listingsProxyConfig: ProxyOptions = {
    ...proxyConfig,
    bypass(request) {
      const pathname = (request.url || "/").split("?")[0];
      const djangoActionPath =
        /^\/listings\/(?:add|dashboard|favorites)(?:\/|$)/.test(pathname) ||
        /^\/listings\/\d+\/(?:edit|delete|favorite)\/?$/.test(pathname);
      return djangoActionPath ? undefined : request.url;
    },
  };
  const djangoPaths = [
    "/api",
    "/accounts",
    "/admin",
    "/about",
    "/anti-scam",
    "/contact",
    "/faq",
    "/how-it-works",
    "/i18n",
    "/media",
    "/messages",
    "/privacy",
    "/robots.txt",
    "/sitemap.xml",
    "/static",
    "/terms",
    "/trust",
  ];

  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      proxy: {
        ...Object.fromEntries(djangoPaths.map((path) => [path, proxyConfig])),
        "/listings": listingsProxyConfig,
      },
    },
  };
});

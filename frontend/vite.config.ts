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
      if (/^\/listings\/\d+\/edit\/?$/.test(pathname)) return request.url;
      return /^\/listings\/\d+\/(?:delete|favorite)\/?$/.test(pathname)
        ? undefined
        : request.url;
    },
  };
  const accountsProxyConfig: ProxyOptions = {
    ...proxyConfig,
    bypass(request) {
      const pathname = (request.url || "/").split("?")[0];
      const reactPage =
        /^\/accounts\/(?:login|register|edit|delete|profile|password_reset(?:\/done)?|reset\/(?:[^/]+\/[^/]+|done))\/?$/.test(pathname) ||
        /^\/accounts\/verify\/(?:sent|resend)\/?$/.test(pathname);
      return reactPage ? request.url : undefined;
    },
  };
  const djangoPaths = [
    "/api",
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
    base: mode === "production" ? "/static/react/" : "/",
    build: {
      outDir: "../static/react",
      emptyOutDir: true,
      manifest: ".vite/manifest.json",
    },
    server: {
      host: "127.0.0.1",
      proxy: {
        ...Object.fromEntries(djangoPaths.map((path) => [path, proxyConfig])),
        "/listings": listingsProxyConfig,
        "/accounts": accountsProxyConfig,
      },
    },
  };
});

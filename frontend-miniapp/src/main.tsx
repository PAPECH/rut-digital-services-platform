import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { PreviewAuthProvider } from "./auth/PreviewAuthProvider";
import { PreviewPage } from "./pages/PreviewPage";
import { I18nProvider } from "@/i18n";
import { PlatformProvider } from "@/features/platform-manifest/model/PlatformProvider";
import { ContentCatalogProvider } from "@/features/content/model/ContentCatalogProvider";
import { HomeContentProvider } from "@/features/content/model/HomeContentProvider";
import { FaqCatalogProvider } from "@/features/faq/model/FaqCatalogProvider";
import { NewsCatalogProvider } from "@/features/news/model/NewsCatalogProvider";
import { api, setToken } from "@/api/client";
import { setBotSlug, resolveBotIdentity } from "@/lib/botSlug";
import { isInsideApp } from "@/max/bridge";
import { UnknownBotScreen } from "@/components/UnknownBotScreen";
import type { PublishedContent } from "@/entities/content/model/types";

import "./styles/globals.css";

interface DraftPreviewResponse {
  content: PublishedContent;
  preview_access_token: string;
  bot_slug: string;
  expires_at: string;
}

function extractPreviewToken(): string | null {
  const match = /^\/preview\/([^/?#]+)/.exec(window.location.pathname);
  return match ? match[1] : null;
}

const root = ReactDOM.createRoot(document.getElementById("root")!);

if (window.location.pathname.startsWith("/preview/")) {
  // Resolve the preview token — and set its scoped access token — BEFORE mounting any provider.
  // ContentCatalogProvider/FaqCatalogProvider fire their own fetch from their very first effect;
  // doing this token fetch inside a mounted component races them and their calls go out
  // unauthenticated (verified: without this, /content/catalog 401s before setToken() lands).
  void (async () => {
    const token = extractPreviewToken();
    if (!token) throw new Error("Ссылка предпросмотра повреждена.");
    const response = await api.get<DraftPreviewResponse>(`/content/preview/${token}`);
    // setBotSlug() must land first -- setToken() namespaces its sessionStorage key by the
    // current bot slug, so storing the token before switching the slug would save it under
    // the wrong (default) key and every subsequent authenticated call would 401.
    setBotSlug(response.bot_slug);
    setToken(response.preview_access_token);
    return response.content;
  })()
    .then((content: PublishedContent) => {
      root.render(
        <React.StrictMode>
          <BrowserRouter>
            <I18nProvider>
              <PlatformProvider>
                <PreviewAuthProvider>
                  <ContentCatalogProvider>
                    <FaqCatalogProvider>
                      <NewsCatalogProvider>
                        <PreviewPage content={content} />
                      </NewsCatalogProvider>
                    </FaqCatalogProvider>
                  </ContentCatalogProvider>
                </PreviewAuthProvider>
              </PlatformProvider>
            </I18nProvider>
          </BrowserRouter>
        </React.StrictMode>,
      );
    })
    .catch((reason: unknown) => {
      root.render(
        <React.StrictMode>
          <div className="screen cms-page-error">
            <h1 className="screen-title">Предпросмотр недоступен</h1>
            <p>{(reason as Error).message}</p>
          </div>
        </React.StrictMode>,
      );
    });
} else if (resolveBotIdentity().status === "unknown") {
  // No `?bot=` param and nothing remembered on this device -- render before any provider that
  // could issue an API call under an unintended bot's identity mounts (Task 034).
  root.render(
    <React.StrictMode>
      <UnknownBotScreen insideMax={isInsideApp()} />
    </React.StrictMode>,
  );
} else {
  root.render(
    <React.StrictMode>
      <BrowserRouter>
        <I18nProvider>
          <PlatformProvider>
            <AuthProvider>
              <ContentCatalogProvider>
                <HomeContentProvider>
                  <FaqCatalogProvider>
                    <NewsCatalogProvider>
                      <App />
                    </NewsCatalogProvider>
                  </FaqCatalogProvider>
                </HomeContentProvider>
              </ContentCatalogProvider>
            </AuthProvider>
          </PlatformProvider>
        </I18nProvider>
      </BrowserRouter>
    </React.StrictMode>,
  );
}

import { createContext, useContext } from "react";

/**
 * True only inside the admin content-builder preview iframe (`/preview/:token`), where there is
 * no real end user behind the request. Blocks that need a real user's data (e.g. submission
 * history) should check this and render a placeholder instead of attempting a doomed fetch.
 */
const PreviewModeContext = createContext(false);

export function PreviewModeProvider({ children }: { children: React.ReactNode }) {
  return <PreviewModeContext.Provider value={true}>{children}</PreviewModeContext.Provider>;
}

export function useIsPreviewMode(): boolean {
  return useContext(PreviewModeContext);
}

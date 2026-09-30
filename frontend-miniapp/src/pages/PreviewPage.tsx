import { useEffect } from "react";

import { useAuth } from "@/auth/AuthProvider";
import type { PublishedContent } from "@/entities/content/model/types";
import { renderTemplate } from "@/lib/renderTemplate";
import { setAnalyticsSuppressed } from "@/features/analytics/api/analyticsApi";
import { PreviewModeProvider } from "@/features/content/model/PreviewModeContext";
import { BlockRendererRegistry } from "@/features/content/ui/renderers/BlockRendererRegistry";

/**
 * Content is already resolved by main.tsx's preview bootstrap before this mounts. Mirrors
 * `HomePage.tsx`'s greeting header for the home singleton (`content.is_home`) -- every other
 * category never renders a header here, matching `ContentCategoryPage.tsx`. The `profile` comes
 * from `PreviewAuthProvider`'s synthetic placeholder, so `{{ profile.first_name }}` templates
 * resolve to a clearly-fake name instead of a real visitor's.
 */
export function PreviewPage({ content }: { content: PublishedContent }) {
  const { profile } = useAuth();

  useEffect(() => {
    setAnalyticsSuppressed(true);
    return () => setAnalyticsSuppressed(false);
  }, []);

  return (
    <PreviewModeProvider>
      <article className="screen cms-page">
        {content.is_home && content.header_visible ? (
          <>
            <h1 className="screen-title">{renderTemplate(content.title, { profile })}</h1>
            {content.subtitle ? (
              <p className="screen-sub">{renderTemplate(content.subtitle, { profile })}</p>
            ) : null}
          </>
        ) : null}
        <div className="cms-page__blocks">
          {content.blocks.map((block) => (
            <BlockRendererRegistry key={block.id} block={block} content={content} />
          ))}
        </div>
      </article>
    </PreviewModeProvider>
  );
}

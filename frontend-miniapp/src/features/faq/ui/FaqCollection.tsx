import { useState } from "react";

import { useAuth } from "@/auth/AuthProvider";
import { Icon } from "@/components/Icon";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { useFaqCatalog } from "@/features/faq/model/FaqCatalogProvider";

interface FaqAnalyticsContext {
  categoryId: number;
  contentVersionId: number;
  blockId: string;
}

export function FaqCollection({
  title,
  analyticsContext,
}: {
  title?: string | null;
  analyticsContext?: FaqAnalyticsContext;
}) {
  const { profile } = useAuth();
  const { items, loading, error } = useFaqCatalog();
  const [openId, setOpenId] = useState<number | null>(null);
  const isEn = Boolean(
    profile?.language_code &&
      !profile.language_code.toLowerCase().startsWith("ru"),
  );

  return (
    <section className="embedded-system-block faq-list-block">
      {title ? <h3 className="section-label">{title}</h3> : null}
      {loading ? (
        <div className="card embedded-system-state">
          {isEn ? "Loading questions…" : "Загрузка вопросов…"}
        </div>
      ) : null}
      {error ? <div className="card form-error">{error}</div> : null}
      {!loading && !error && items.length === 0 ? (
        <div className="card embedded-system-state">
          {isEn ? "No FAQ yet" : "Пока вопросов нет"}
        </div>
      ) : null}
      {!loading && !error
        ? items.map((item) => {
            const question = item.question;
            const answer = item.answer;
            const open = openId === item.id;
            const answerId = `faq-answer-${item.id}`;

            return (
              <div key={item.id} className="faq-item">
                <button
                  type="button"
                  className="faq-q"
                  aria-expanded={open}
                  aria-controls={answerId}
                  onClick={() => {
                    if (!open) {
                      trackAnalyticsEventInBackground({
                        action_type: "faq_open",
                        source_surface: analyticsContext ? "category" : "direct",
                        faq_id: item.id,
                        category_id: analyticsContext?.categoryId,
                        content_version_id: analyticsContext?.contentVersionId,
                        block_id: analyticsContext?.blockId,
                      });
                    }
                    setOpenId(open ? null : item.id);
                  }}
                >
                  <span>{question}</span>
                  <span
                    className="ico"
                    aria-hidden="true"
                    style={{
                      width: 18,
                      height: 18,
                      color: "var(--ink-400)",
                      transform: open ? "rotate(180deg)" : "none",
                      transition: "transform .15s",
                    }}
                  >
                    <Icon.ChevronDown />
                  </span>
                </button>
                {open ? (
                  <div id={answerId} className="faq-a">
                    {answer}
                  </div>
                ) : null}
              </div>
            );
          })
        : null}
    </section>
  );
}

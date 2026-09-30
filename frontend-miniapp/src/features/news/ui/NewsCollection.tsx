import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { newsApi } from "@/features/news/api/newsApi";
import { newsExcerpt } from "@/features/news/model/excerpt";
import { useNewsCatalog } from "@/features/news/model/NewsCatalogProvider";
import { NewsBodyBlockView } from "@/features/news/ui/NewsBodyBlockView";
import type { NewsItem } from "@/entities/news/model/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

export function NewsCollection({ title }: { title?: string | null }) {
  const { items, loading, error } = useNewsCatalog();
  const [openItem, setOpenItem] = useState<NewsItem | null>(null);

  useEffect(() => {
    newsApi.recordOpen().catch(() => undefined);
  }, []);

  if (openItem) {
    return <NewsDetail item={openItem} onBack={() => setOpenItem(null)} />;
  }

  return (
    <section className="embedded-system-block news-list-block">
      {title ? <h3 className="section-label">{title}</h3> : null}
      {loading ? <div className="card embedded-system-state">Загрузка новостей…</div> : null}
      {error ? <div className="card form-error">{error}</div> : null}
      {!loading && !error && items.length === 0 ? (
        <div className="card embedded-system-state">Пока новостей нет</div>
      ) : null}
      {!loading && !error
        ? items.map((item) => {
            const excerpt = newsExcerpt(item.body_blocks);
            return (
              <button
                type="button"
                key={item.id}
                className="news-card"
                onClick={() => {
                  newsApi.recordItemOpen(item.id).catch(() => undefined);
                  setOpenItem(item);
                }}
              >
                {item.cover_url ? (
                  <img className="news-card__cover" src={item.cover_url} alt="" />
                ) : null}
                <div className="news-card__body">
                  <div className="news-card__title">{item.title}</div>
                  {excerpt ? <div className="news-card__excerpt">{excerpt}</div> : null}
                  <div className="news-card__footer">
                    {item.category ? (
                      <span className="news-card__category">{item.category}</span>
                    ) : (
                      <span />
                    )}
                    <span className="news-card__date">{formatDate(item.published_at)}</span>
                  </div>
                </div>
              </button>
            );
          })
        : null}
    </section>
  );
}

function NewsDetail({ item, onBack }: { item: NewsItem; onBack: () => void }) {
  return (
    <div className="news-detail">
      <button type="button" className="news-detail__back" onClick={onBack}>
        <span className="ico" aria-hidden="true">
          <Icon.ArrowLeft />
        </span>
        Назад к новостям
      </button>
      {item.cover_url ? <img className="news-detail__cover" src={item.cover_url} alt="" /> : null}
      <div className="news-detail__meta">
        <span>{formatDate(item.published_at)}</span>
        {item.category ? <span className="news-card__category">{item.category}</span> : null}
      </div>
      <h1 className="news-detail__title">{item.title}</h1>
      <div className="news-detail__body">
        {item.body_blocks.map((block) => (
          <NewsBodyBlockView key={block.id} block={block} attachmentUrls={item.attachment_urls} />
        ))}
      </div>
    </div>
  );
}

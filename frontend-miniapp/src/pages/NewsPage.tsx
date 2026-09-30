import { NewsCollection } from "@/features/news/ui/NewsCollection";

export function NewsPage() {
  return (
    <div className="screen">
      <h1 className="screen-title">Новости</h1>
      <NewsCollection />
    </div>
  );
}

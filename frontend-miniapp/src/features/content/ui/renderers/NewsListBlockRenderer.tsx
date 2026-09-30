import type {
  BlockRendererProps,
  NewsListBlock,
} from "@/entities/content/model/types";
import { NewsCollection } from "@/features/news/ui/NewsCollection";

export function NewsListBlockRenderer({ block }: BlockRendererProps<NewsListBlock>) {
  return <NewsCollection title={block.title} />;
}

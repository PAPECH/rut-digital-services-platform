import type {
  AttachmentUrlEntry,
  NewsBodyBlock,
} from "@/entities/content/model/types";

export interface NewsItem {
  id: number;
  title: string;
  title_en: string | null;
  body_blocks: NewsBodyBlock[];
  category: string | null;
  cover_url: string | null;
  is_active: boolean;
  published_at: string;
  attachment_urls: Record<number, AttachmentUrlEntry>;
}

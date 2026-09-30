import type { ContentIconName } from '@/entities/content/model/contentIcons'

// A `paragraph`/`callout` block's text is either a legacy plain string (unformatted -- rendered
// exactly as-is, may belong to an already-published, immutable content version) or this typed
// rich-text document written by the admin's WYSIWYG editor. Mirrors backend
// `content_blocks.domain.rich_text` / frontend-admin's `entities/content/model/types.ts`.
export type RichTextMark = 'bold' | 'italic' | 'underline' | 'strike'

export interface RichTextRun {
  text: string
  marks: RichTextMark[]
  href: string | null
}

export interface RichTextParagraphNode {
  type: 'paragraph'
  runs: RichTextRun[]
}

export interface RichTextListNode {
  type: 'bullet_list' | 'ordered_list'
  items: RichTextRun[][]
}

export type RichTextNode = RichTextParagraphNode | RichTextListNode

export interface RichTextDoc {
  format: 'rich_text_v1'
  nodes: RichTextNode[]
}

export type FormattedText = string | RichTextDoc

export interface HeadingBlock {
  id: string
  type: 'heading'
  text: string
  level: 1 | 2 | 3 | 4 | 5 | 6
}
export interface ParagraphBlock {
  id: string
  type: 'paragraph'
  text: FormattedText
}
export interface CalloutBlock {
  id: string
  type: 'callout'
  title: string | null
  text: FormattedText
  tone: 'info' | 'warning' | 'success' | 'danger'
}
export interface ContactListBlock {
  id: string
  type: 'contact_list'
  items: Array<{ label: string; value: string; href: string | null }>
}
export interface TitledItem {
  id: string
  title: string
  text: string
}
export interface AccordionBlock {
  id: string
  type: 'accordion'
  items: TitledItem[]
}
export interface StepsBlock {
  id: string
  type: 'steps'
  items: TitledItem[]
}
export interface LinkBlock {
  id: string
  type: 'link'
  title: string
  href: string
  style: 'card' | 'button'
  external: boolean
}
export type FileDisplayMode = 'tile' | 'inline_image'

export interface FileListBlock {
  id: string
  type: 'file_list'
  items: Array<{
    attachment_id: number
    title: string
    description: string | null
    display_mode: FileDisplayMode
  }>
}
export interface FormActionBlock {
  id: string
  type: 'form_action'
  form_id: number
  title: string
  description: string | null
}
export interface TestActionBlock {
  id: string
  type: 'test_action'
  test_id: number
  title: string
  description: string | null
}
export interface CapabilityActionBlock {
  id: string
  type: 'capability_action'
  capability_key: string
  view_key: string
  title: string
  description: string | null
}
export interface CategoryGridBlock {
  id: string
  type: 'category_grid'
  parent_id: number | null
  title: string | null
}
export interface FormCatalogBlock {
  id: string
  type: 'form_catalog'
  title: string | null
}
export interface SubmissionHistoryBlock {
  id: string
  type: 'submission_history'
  title: string | null
}
export interface TestCatalogBlock {
  id: string
  type: 'test_catalog'
  title: string | null
}
export interface TestAttemptHistoryBlock {
  id: string
  type: 'test_attempt_history'
  title: string | null
}
export interface FaqListBlock {
  id: string
  type: 'faq_list'
  title: string | null
}
export interface NewsListBlock {
  id: string
  type: 'news_list'
  title: string | null
}

export type NestedContentBlock =
  | HeadingBlock
  | ParagraphBlock
  | CalloutBlock
  | ContactListBlock
  | AccordionBlock
  | StepsBlock
  | LinkBlock
  | FileListBlock
  | FormActionBlock
  | TestActionBlock
  | CapabilityActionBlock

// The content-shaping subset shared with a news item's body (backend `content_blocks` shared
// kernel) -- navigational blocks don't apply inside a single news article.
export type NewsBodyBlock =
  | HeadingBlock
  | ParagraphBlock
  | CalloutBlock
  | ContactListBlock
  | LinkBlock
  | FileListBlock
export type NewsBodyBlockType = NewsBodyBlock['type']

export interface TabsBlock {
  id: string
  type: 'tabs'
  tabs: Array<{ key: string; title: string; blocks: NestedContentBlock[] }>
}
export type ContentBlock =
  | NestedContentBlock
  | TabsBlock
  | CategoryGridBlock
  | FormCatalogBlock
  | SubmissionHistoryBlock
  | TestCatalogBlock
  | TestAttemptHistoryBlock
  | FaqListBlock
  | NewsListBlock
export type ContentBlockType = ContentBlock['type']
export type NestedContentBlockType = NestedContentBlock['type']

export interface PublishedCategorySummary {
  id: number
  slug: string
  parent_id: number | null
  icon: ContentIconName
  order: number
  title: string
  subtitle: string | null
  // null only for a capability shortcut (Task 044), which has no content version.
  version_id: number | null
  version: number | null
  is_filled: boolean
  image_url: string | null
  // Both set -> a capability shortcut tile: tapping it opens this capability's view (resolved
  // via the platform manifest) instead of /content/{slug}.
  capability_key: string | null
  capability_view_key: string | null
}

export interface AttachmentUrlEntry {
  url: string
  mime: string
}

export interface PublishedContent extends PublishedCategorySummary {
  language: string
  blocks: ContentBlock[]
  attachment_urls: Record<number, AttachmentUrlEntry>
  published_at: string
  header_visible: boolean
  is_home: boolean
}

export interface BlockRendererProps<T extends ContentBlock = ContentBlock> {
  block: T
  content: PublishedContent
}

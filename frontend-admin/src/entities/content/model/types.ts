import type { ContentIconName } from '@/entities/content/model/contentIcons'

export type CalloutTone = 'info' | 'warning' | 'success' | 'danger'

// A `paragraph`/`callout` block's text is either a legacy plain string (unformatted -- rendered
// exactly as typed, may belong to an already-published, immutable content version) or this typed
// rich-text document -- the only shape the WYSIWYG editor ever writes. There is no third,
// arbitrary-HTML shape; see backend `content_blocks.domain.rich_text` for the authoritative
// contract this mirrors.
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
  tone: CalloutTone
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
// kernel) -- navigational blocks (accordion/steps/form_action/capability_action and page-level
// system blocks) don't apply inside a single news article.
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

export interface ContentDraft {
  category_id: number
  title: string
  subtitle: string | null
  language: string
  blocks: ContentBlock[]
  revision: number
  is_shared: boolean
  is_filled: boolean
  image_url: string | null
  header_visible: boolean
}

export interface AdminContentCategory {
  id: number
  slug: string
  parent_id: number | null
  icon: ContentIconName
  order: number
  is_active: boolean
  published_version_id: number | null
  last_published_revision: number
  is_home: boolean
  is_filled: boolean
  image_url: string | null
  // Both set -> a capability shortcut instead of a content page (Task 044); `draft` is then
  // null (a shortcut has no draft/version) and `title`/`subtitle` carry its own card text.
  capability_key: string | null
  capability_view_key: string | null
  title: string | null
  subtitle: string | null
  draft: ContentDraft | null
}

export function isShortcutCategory(category: AdminContentCategory): boolean {
  return category.capability_key !== null && category.capability_view_key !== null
}

export interface AttachmentUrlEntry {
  url: string
  mime: string
}

export interface PublishedContent {
  id: number
  slug: string
  parent_id: number | null
  icon: ContentIconName
  order: number
  title: string
  subtitle: string | null
  version_id: number
  version: number
  language: string
  blocks: ContentBlock[]
  attachment_urls: Record<number, AttachmentUrlEntry>
  published_at: string
}

export interface ContentCategoryCreate {
  slug: string
  parent_id: number | null
  icon: ContentIconName
  title: string
  subtitle: string | null
  language: string
  order: number
  // Both set -> create a capability shortcut instead of a content page (Task 044).
  capability_key?: string | null
  capability_view_key?: string | null
  image_url?: string | null
}

export interface ContentShortcutCardPatch {
  icon?: ContentIconName
  title?: string
  subtitle?: string | null
  image_url?: string | null
}

export interface ContentAttachmentReference {
  category_id: number
  usage: 'card_image' | 'file_list_item'
}

export interface ContentAttachmentOption {
  id: number
  name: string
  mime: string
  size_bytes: number
  url: string
  created_at: string
  referenced_by_draft: ContentAttachmentReference[]
  referenced_by_published: ContentAttachmentReference[]
}

export interface ContentAttachmentPage {
  items: ContentAttachmentOption[]
  total: number
}

export interface ContentFormOption {
  id: number
  name: string
}

export interface ContentTestOption {
  id: number
  name: string
}

export interface SharedContentDraft {
  source_category_id: number
  source_bot_instance_id: number
  source_bot_name: string
  slug: string
  title: string
  subtitle: string | null
  icon: ContentIconName
  language: string
}

export interface ContentFormDependencyTarget {
  kind: 'form'
  id: number
  slug: string
  label: string
}

export type ContentFormDependencyStatus = 'resolved' | 'copy_available' | 'mapping_required' | 'unavailable'

export interface ContentFormDependency {
  kind: 'form'
  source_id: number
  source_slug: string | null
  label: string
  status: ContentFormDependencyStatus
  can_copy: boolean
  matched_target_id: number | null
  matched_target_ready: boolean
}

export interface ContentDependencyBlocker {
  kind: 'file'
  code: 'file_copy_not_supported'
  count: number
}

export interface SharedContentDependencyReport {
  dependencies: ContentFormDependency[]
  targets: ContentFormDependencyTarget[]
  blockers: ContentDependencyBlocker[]
}

export type ContentFormDependencyResolution =
  | {
      kind: 'form'
      source_id: number
      action: 'use_existing'
      target_id: number
    }
  | {
      kind: 'form'
      source_id: number
      action: 'copy_shared'
    }

export interface ResolvedContentFormDependency {
  kind: 'form'
  source_id: number
  target_id: number
  action: 'matched_slug' | 'use_existing' | 'copy_shared'
  target_ready: boolean
}

export interface SharedContentImportResult {
  category: AdminContentCategory
  dependencies: ResolvedContentFormDependency[]
}

export interface BlockEditorProps<T extends ContentBlock = ContentBlock> {
  block: T
  onChange: (block: T) => void
}

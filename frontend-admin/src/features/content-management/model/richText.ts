import type {
  FormattedText,
  RichTextDoc,
  RichTextMark,
  RichTextNode,
  RichTextRun,
} from '@/entities/content/model/types'

// Maps between our typed rich-text contract (mirrors backend
// `content_blocks.domain.rich_text`) and Tiptap/ProseMirror's own JSON document shape. Tiptap is
// only ever a presentation-layer detail: the editor's native document model is converted to and
// from this fixed contract at the editor boundary, so what gets persisted and sent to the API
// never depends on which editor library rendered it.

const MARK_TYPES: RichTextMark[] = ['bold', 'italic', 'underline', 'strike']

interface PmMark {
  type: string
  attrs?: { href?: string }
}

interface PmTextNode {
  type: 'text'
  text: string
  marks?: PmMark[]
}

interface PmParagraphNode {
  type: 'paragraph'
  content?: PmTextNode[]
}

interface PmListItemNode {
  type: 'listItem'
  content?: PmParagraphNode[]
}

interface PmListNode {
  type: 'bulletList' | 'orderedList'
  content?: PmListItemNode[]
}

type PmBlockNode = PmParagraphNode | PmListNode

export interface PmDoc {
  type: 'doc'
  content: PmBlockNode[]
}

function runFromPmText(node: PmTextNode): RichTextRun {
  const marks = (node.marks ?? []).filter((mark): mark is PmMark =>
    (MARK_TYPES as string[]).includes(mark.type),
  )
  const linkMark = (node.marks ?? []).find((mark) => mark.type === 'link')
  return {
    text: node.text,
    marks: marks.map((mark) => mark.type as RichTextMark),
    href: linkMark?.attrs?.href ?? null,
  }
}

function runsFromPmParagraph(node: PmParagraphNode): RichTextRun[] {
  return (node.content ?? [])
    .filter((child): child is PmTextNode => child.type === 'text')
    .map(runFromPmText)
}

/** Converts Tiptap's `editor.getJSON()` output into our typed rich-text document. */
export function pmDocToRichText(doc: PmDoc): RichTextDoc {
  const nodes: RichTextNode[] = []
  for (const block of doc.content) {
    if (block.type === 'paragraph') {
      const runs = runsFromPmParagraph(block)
      if (runs.length > 0) nodes.push({ type: 'paragraph', runs })
    } else if (block.type === 'bulletList' || block.type === 'orderedList') {
      const items = (block.content ?? [])
        .map((item) => (item.content ?? []).flatMap(runsFromPmParagraph))
        .filter((runs) => runs.length > 0)
      if (items.length > 0) nodes.push({ type: block.type === 'bulletList' ? 'bullet_list' : 'ordered_list', items })
    }
  }
  return { format: 'rich_text_v1', nodes }
}

function runToPmText(run: RichTextRun): PmTextNode {
  const marks: PmMark[] = run.marks.map((mark) => ({ type: mark }))
  if (run.href) marks.push({ type: 'link', attrs: { href: run.href } })
  return { type: 'text', text: run.text, marks: marks.length > 0 ? marks : undefined }
}

function pmParagraphFromRuns(runs: RichTextRun[]): PmParagraphNode {
  const content = runs.filter((run) => run.text.length > 0).map(runToPmText)
  return content.length > 0 ? { type: 'paragraph', content } : { type: 'paragraph' }
}

/** Converts our typed rich-text document (or a legacy plain string) into a Tiptap-loadable
 * ProseMirror JSON document, used as `useEditor({ content })`. */
export function formattedTextToPmDoc(value: FormattedText): PmDoc {
  if (typeof value === 'string') {
    const lines = value.split('\n')
    return {
      type: 'doc',
      content: lines.map((line) => pmParagraphFromRuns(line ? [{ text: line, marks: [], href: null }] : [])),
    }
  }
  const content: PmBlockNode[] = value.nodes.map((node) => {
    if (node.type === 'paragraph') return pmParagraphFromRuns(node.runs)
    return {
      type: node.type === 'bullet_list' ? 'bulletList' : 'orderedList',
      content: node.items.map((runs) => ({ type: 'listItem', content: [pmParagraphFromRuns(runs)] })),
    }
  })
  return { type: 'doc', content: content.length > 0 ? content : [{ type: 'paragraph' }] }
}

/** Plain-text preview of a formatted value, e.g. for list/card excerpts. */
export function formattedTextToPlainText(value: FormattedText): string {
  if (typeof value === 'string') return value
  return value.nodes
    .map((node) => {
      if (node.type === 'paragraph') return node.runs.map((run) => run.text).join('')
      return node.items.map((runs) => runs.map((run) => run.text).join('')).join('\n')
    })
    .join('\n')
}

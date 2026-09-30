import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

import type { FormattedText } from '@/entities/content/model/types'
import { formattedTextToPmDoc, pmDocToRichText, type PmDoc } from '../model/richText'

interface RichTextEditorProps {
  value: FormattedText
  onChange: (value: FormattedText) => void
  rows?: number
}

/** WYSIWYG editor for a `paragraph`/`callout` block's text -- bold/italic/underline/strike,
 * bulleted/numbered lists, and inline links. Reads and writes only the typed rich-text contract
 * (see `../model/richText`); Tiptap's own document model never leaves this component.
 *
 * Uncontrolled by design once mounted: `value` seeds the editor's initial content, and after that
 * Tiptap owns the document -- every keystroke, mark toggle, and selection change lives entirely
 * in its own state. Do NOT add an effect that calls `setContent()` whenever the `value` prop
 * changes: since `onUpdate` below feeds every edit straight back into `value` via the parent's
 * state, that would re-run on every keystroke and force the editor's live document/selection back
 * to a freshly-parsed copy mid-edit. That previously caused exactly this bug: double-clicking a
 * word (a normal selection) raced against a content reset, leaving the "marks to apply to the
 * next typed character" stuck on bold with no selection left to toggle it off through. If a
 * *different* block's text needs to load into this component, remount it instead (the callers
 * key each `<RichTextEditor>` by the block's stable id) rather than pushing a new `value` into a
 * live instance.
 *
 * Never render this inside a `<label>` (use `EditorFieldGroup`): a label forwards every click in
 * its area to its first button — the «Ж» toolbar button — so selecting text would bold it. */
export function RichTextEditor({ value, onChange, rows = 5 }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: formattedTextToPmDoc(value) as unknown as Record<string, unknown>,
    onUpdate: ({ editor: instance }) => {
      onChange(pmDocToRichText(instance.getJSON() as PmDoc))
    },
    editorProps: {
      attributes: {
        class: 'rich-text-editor__content',
        style: `min-height: ${rows * 1.5}em`,
      },
    },
  })

  if (!editor) return null

  const button = (
    label: string,
    isActive: boolean,
    onClick: () => void,
    title: string,
  ) => (
    <button
      type="button"
      className={`rich-text-toolbar__btn${isActive ? ' is-active' : ''}`}
      title={title}
      // Keep focus and the selection in the editor while pressing a toolbar button.
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
    >
      {label}
    </button>
  )

  const setLink = () => {
    const previous = editor.getAttributes('link').href as string | undefined
    const href = window.prompt('Ссылка (https://...)', previous ?? '')
    if (href === null) return
    if (href === '') {
      editor.chain().focus().unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href }).run()
  }

  return (
    <div className="rich-text-editor">
      <div className="rich-text-toolbar">
        {button('Ж', editor.isActive('bold'), () => editor.chain().focus().toggleBold().run(), 'Жирный')}
        {button('К', editor.isActive('italic'), () => editor.chain().focus().toggleItalic().run(), 'Курсив')}
        {button('Ч', editor.isActive('underline'), () => editor.chain().focus().toggleUnderline().run(), 'Подчёркнутый')}
        {button('S', editor.isActive('strike'), () => editor.chain().focus().toggleStrike().run(), 'Зачёркнутый')}
        <span className="rich-text-toolbar__sep" />
        {button('•', editor.isActive('bulletList'), () => editor.chain().focus().toggleBulletList().run(), 'Список')}
        {button('1.', editor.isActive('orderedList'), () => editor.chain().focus().toggleOrderedList().run(), 'Нумерованный список')}
        <span className="rich-text-toolbar__sep" />
        {button('🔗', editor.isActive('link'), setLink, 'Ссылка')}
      </div>
      <EditorContent editor={editor} className="rich-text-editor__container" />
    </div>
  )
}

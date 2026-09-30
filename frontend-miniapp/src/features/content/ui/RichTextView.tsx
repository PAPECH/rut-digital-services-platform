import type { FormattedText, RichTextRun } from '@/entities/content/model/types'

function RunView({ run }: { run: RichTextRun }) {
  let node: React.ReactNode = run.text
  if (run.marks.includes('bold')) node = <strong>{node}</strong>
  if (run.marks.includes('italic')) node = <em>{node}</em>
  if (run.marks.includes('underline')) node = <u>{node}</u>
  if (run.marks.includes('strike')) node = <s>{node}</s>
  if (run.href) {
    node = (
      <a href={run.href} target="_blank" rel="noreferrer">
        {node}
      </a>
    )
  }
  return <>{node}</>
}

/** Renders a `paragraph`/`callout` block's text -- either the legacy plain string (unchanged,
 * unformatted) or the typed rich-text document (bold/italic/underline/strike, bulleted/numbered
 * lists, inline links) written by the admin's WYSIWYG editor. `className` is applied to each
 * rendered paragraph, matching how the plain-string case is styled today. */
export function RichTextView({
  value,
  className,
}: {
  value: FormattedText
  className?: string
}) {
  if (typeof value === 'string') {
    return <p className={className}>{value}</p>
  }
  return (
    <>
      {value.nodes.map((node, index) => {
        if (node.type === 'paragraph') {
          return (
            <p className={className} key={index}>
              {node.runs.map((run, runIndex) => (
                <RunView run={run} key={runIndex} />
              ))}
            </p>
          )
        }
        const ListTag = node.type === 'bullet_list' ? 'ul' : 'ol'
        return (
          <ListTag key={index}>
            {node.items.map((runs, itemIndex) => (
              <li key={itemIndex}>
                {runs.map((run, runIndex) => (
                  <RunView run={run} key={runIndex} />
                ))}
              </li>
            ))}
          </ListTag>
        )
      })}
    </>
  )
}

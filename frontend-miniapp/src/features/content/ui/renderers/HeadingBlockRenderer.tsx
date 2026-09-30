import type { BlockRendererProps, HeadingBlock } from '@/entities/content/model/types'

export function HeadingBlockRenderer({ block }: BlockRendererProps<HeadingBlock>) {
  const level = block.level >= 1 && block.level <= 6 ? block.level : 2
  const Tag = `h${level}` as keyof JSX.IntrinsicElements

  return <Tag className={`cms-heading cms-heading--${level}`}>{block.text}</Tag>
}

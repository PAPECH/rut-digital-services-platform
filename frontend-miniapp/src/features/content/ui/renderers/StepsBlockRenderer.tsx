import type {
  BlockRendererProps,
  StepsBlock,
} from "@/entities/content/model/types";

export function StepsBlockRenderer({ block }: BlockRendererProps<StepsBlock>) {
  return (
    <ol className="cms-steps">
      {block.items.map((item, index) => (
        <li key={item.id}>
          <span className="cms-steps__number">{index + 1}</span>
          <div>
            <strong>{item.title}</strong>
            <p>{item.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

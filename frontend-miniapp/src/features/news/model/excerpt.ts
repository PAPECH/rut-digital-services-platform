import type { FormattedText, NewsBodyBlock } from "@/entities/content/model/types";

const MAX_EXCERPT_LENGTH = 100;

function plainText(value: FormattedText): string {
  if (typeof value === "string") return value;
  return value.nodes
    .map((node) => {
      if (node.type === "paragraph") return node.runs.map((run) => run.text).join("");
      return node.items.map((runs) => runs.map((run) => run.text).join("")).join(" ");
    })
    .join(" ");
}

/** First ~100 characters of a news item's body, for the card preview -- the first non-empty
 * `paragraph` block's text, falling back to `heading` if the body opens with one instead. */
export function newsExcerpt(blocks: NewsBodyBlock[], maxLength = MAX_EXCERPT_LENGTH): string {
  for (const block of blocks) {
    const text =
      block.type === "paragraph"
        ? plainText(block.text).trim()
        : block.type === "heading"
          ? block.text.trim()
          : "";
    if (text) {
      return text.length > maxLength ? `${text.slice(0, maxLength).trimEnd()}…` : text;
    }
  }
  return "";
}

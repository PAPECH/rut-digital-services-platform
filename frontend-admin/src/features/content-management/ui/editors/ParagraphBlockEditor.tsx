import type {
  BlockEditorProps,
  ParagraphBlock,
} from "@/entities/content/model/types";
import { RichTextEditor } from "../RichTextEditor";
import { EditorFieldGroup } from "./EditorFields";

export function ParagraphBlockEditor({
  block,
  onChange,
}: BlockEditorProps<ParagraphBlock>) {
  return (
    <EditorFieldGroup label="Текст">
      <RichTextEditor
        key={block.id}
        value={block.text}
        onChange={(text) => onChange({ ...block, text })}
      />
    </EditorFieldGroup>
  );
}

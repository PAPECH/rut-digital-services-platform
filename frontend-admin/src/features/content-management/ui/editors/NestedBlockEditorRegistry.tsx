import type { ComponentType } from "react";

import type {
  BlockEditorProps,
  NestedContentBlock,
  NestedContentBlockType,
} from "@/entities/content/model/types";
import { AccordionBlockEditor } from "./AccordionBlockEditor";
import { CalloutBlockEditor } from "./CalloutBlockEditor";
import { CapabilityActionBlockEditor } from "./CapabilityActionBlockEditor";
import { ContactListBlockEditor } from "./ContactListBlockEditor";
import { FileListBlockEditor } from "./FileListBlockEditor";
import { FormActionBlockEditor } from "./FormActionBlockEditor";
import { TestActionBlockEditor } from "./TestActionBlockEditor";
import { HeadingBlockEditor } from "./HeadingBlockEditor";
import { LinkBlockEditor } from "./LinkBlockEditor";
import { ParagraphBlockEditor } from "./ParagraphBlockEditor";
import { StepsBlockEditor } from "./StepsBlockEditor";

type Registry = {
  [Type in NestedContentBlockType]: ComponentType<
    BlockEditorProps<Extract<NestedContentBlock, { type: Type }>>
  >;
};

export const nestedBlockEditorRegistry = {
  heading: HeadingBlockEditor,
  paragraph: ParagraphBlockEditor,
  callout: CalloutBlockEditor,
  contact_list: ContactListBlockEditor,
  accordion: AccordionBlockEditor,
  steps: StepsBlockEditor,
  link: LinkBlockEditor,
  file_list: FileListBlockEditor,
  form_action: FormActionBlockEditor,
  test_action: TestActionBlockEditor,
  capability_action: CapabilityActionBlockEditor,
} satisfies Registry;

export function NestedBlockEditorRegistry({
  block,
  onChange,
}: BlockEditorProps<NestedContentBlock>) {
  const Editor = nestedBlockEditorRegistry[block.type] as ComponentType<
    BlockEditorProps<NestedContentBlock>
  >;
  return <Editor block={block} onChange={onChange} />;
}

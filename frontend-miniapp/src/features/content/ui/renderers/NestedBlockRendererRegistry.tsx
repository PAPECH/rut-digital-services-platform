import type { ComponentType } from "react";

import type {
  BlockRendererProps,
  NestedContentBlock,
  NestedContentBlockType,
} from "@/entities/content/model/types";
import { AccordionBlockRenderer } from "./AccordionBlockRenderer";
import { CalloutBlockRenderer } from "./CalloutBlockRenderer";
import { CapabilityActionBlockRenderer } from "./CapabilityActionBlockRenderer";
import { ContactListBlockRenderer } from "./ContactListBlockRenderer";
import { FileListBlockRenderer } from "./FileListBlockRenderer";
import { FormActionBlockRenderer } from "./FormActionBlockRenderer";
import { TestActionBlockRenderer } from "./TestActionBlockRenderer";
import { HeadingBlockRenderer } from "./HeadingBlockRenderer";
import { LinkBlockRenderer } from "./LinkBlockRenderer";
import { ParagraphBlockRenderer } from "./ParagraphBlockRenderer";
import { StepsBlockRenderer } from "./StepsBlockRenderer";

type Registry = {
  [Type in NestedContentBlockType]: ComponentType<
    BlockRendererProps<Extract<NestedContentBlock, { type: Type }>>
  >;
};

export const nestedBlockRendererRegistry = {
  heading: HeadingBlockRenderer,
  paragraph: ParagraphBlockRenderer,
  callout: CalloutBlockRenderer,
  contact_list: ContactListBlockRenderer,
  accordion: AccordionBlockRenderer,
  steps: StepsBlockRenderer,
  link: LinkBlockRenderer,
  file_list: FileListBlockRenderer,
  form_action: FormActionBlockRenderer,
  test_action: TestActionBlockRenderer,
  capability_action: CapabilityActionBlockRenderer,
} satisfies Registry;

export function NestedBlockRendererRegistry(
  props: BlockRendererProps<NestedContentBlock>,
) {
  const Renderer = nestedBlockRendererRegistry[
    props.block.type
  ] as ComponentType<BlockRendererProps<NestedContentBlock>>;
  return <Renderer {...props} />;
}

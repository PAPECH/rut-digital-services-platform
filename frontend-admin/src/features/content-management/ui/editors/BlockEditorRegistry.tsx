import type { ComponentType } from "react";

import type {
  BlockEditorProps,
  ContentBlock,
  ContentBlockType,
} from "@/entities/content/model/types";
import { nestedBlockEditorRegistry } from "./NestedBlockEditorRegistry";
import { FormCatalogBlockEditor } from "./FormCatalogBlockEditor";
import { TestCatalogBlockEditor } from "./TestCatalogBlockEditor";
import { FaqListBlockEditor } from "./FaqListBlockEditor";
import { NewsListBlockEditor } from "./NewsListBlockEditor";
import { SubmissionHistoryBlockEditor } from "./SubmissionHistoryBlockEditor";
import { TestAttemptHistoryBlockEditor } from "./TestAttemptHistoryBlockEditor";
import { CategoryGridBlockEditor } from "./CategoryGridBlockEditor";
import { TabsBlockEditor } from "./TabsBlockEditor";

type Registry = {
  [Type in ContentBlockType]: ComponentType<
    BlockEditorProps<Extract<ContentBlock, { type: Type }>>
  >;
};

export const blockEditorRegistry = {
  ...nestedBlockEditorRegistry,
  form_catalog: FormCatalogBlockEditor,
  test_catalog: TestCatalogBlockEditor,
  submission_history: SubmissionHistoryBlockEditor,
  test_attempt_history: TestAttemptHistoryBlockEditor,
  faq_list: FaqListBlockEditor,
  news_list: NewsListBlockEditor,
  category_grid: CategoryGridBlockEditor,
  tabs: TabsBlockEditor,
} satisfies Registry;

export function BlockEditorRegistry({ block, onChange }: BlockEditorProps) {
  const Editor = blockEditorRegistry[
    block.type
  ] as ComponentType<BlockEditorProps>;
  return <Editor block={block} onChange={onChange} />;
}

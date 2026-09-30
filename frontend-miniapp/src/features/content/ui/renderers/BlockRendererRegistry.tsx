import type { ComponentType } from "react";

import type {
  BlockRendererProps,
  ContentBlock,
  ContentBlockType,
} from "@/entities/content/model/types";
import { nestedBlockRendererRegistry } from "./NestedBlockRendererRegistry";
import { CategoryGridBlockRenderer } from "./CategoryGridBlockRenderer";
import { FaqListBlockRenderer } from "./FaqListBlockRenderer";
import { NewsListBlockRenderer } from "./NewsListBlockRenderer";
import { FormCatalogBlockRenderer } from "./FormCatalogBlockRenderer";
import { TestCatalogBlockRenderer } from "./TestCatalogBlockRenderer";
import { SubmissionHistoryBlockRenderer } from "./SubmissionHistoryBlockRenderer";
import { TestAttemptHistoryBlockRenderer } from "./TestAttemptHistoryBlockRenderer";
import { TabsBlockRenderer } from "./TabsBlockRenderer";

type Registry = {
  [Type in ContentBlockType]: ComponentType<
    BlockRendererProps<Extract<ContentBlock, { type: Type }>>
  >;
};

export const blockRendererRegistry = {
  ...nestedBlockRendererRegistry,
  category_grid: CategoryGridBlockRenderer,
  faq_list: FaqListBlockRenderer,
  news_list: NewsListBlockRenderer,
  form_catalog: FormCatalogBlockRenderer,
  test_catalog: TestCatalogBlockRenderer,
  submission_history: SubmissionHistoryBlockRenderer,
  test_attempt_history: TestAttemptHistoryBlockRenderer,
  tabs: TabsBlockRenderer,
} satisfies Registry;

export function BlockRendererRegistry(props: BlockRendererProps) {
  const Renderer = blockRendererRegistry[props.block.type] as
    ComponentType<BlockRendererProps> | undefined;
  return Renderer ? (
    <Renderer {...props} />
  ) : (
    <div className="cms-unsupported">Этот блок пока не поддерживается.</div>
  );
}

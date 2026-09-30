import type { ComponentType } from "react";

import type { ContentBlockType } from "@/entities/content/model/types";
import { ContactListExample, LinkButtonExample, LinkCardExample } from "./ContactBlockExamples";
import { CapabilityActionExample, FaqListExample, NewsListExample } from "./DynamicBlockExamples";
import { FileInlineImageExample, FileTileExample } from "./FileBlockExamples";
import {
  FormActionExample,
  FormCatalogExample,
  SubmissionHistoryExample,
  TestActionExample,
  TestAttemptHistoryExample,
  TestCatalogExample,
} from "./FormBlockExamples";
import {
  AccordionExample,
  CategoryGridExample,
  StepsExample,
  TabsExample,
} from "./StructureBlockExamples";
import {
  CalloutExample,
  HeadingLevelsExample,
  HeadingPageExample,
  ParagraphExample,
} from "./TextBlockExamples";

/**
 * Student-side mockups per block type. A block with several display options in its editor lists
 * one variant per option, captioned with the editor's own wording. A full `Record`, so a new
 * block type needs an example.
 */
export interface BlockExampleVariant {
  caption?: string;
  Component: ComponentType;
  /** The mockup reacts to taps (open/switch/preview) — marked with «👆 Можно нажимать». */
  interactive?: boolean;
}

const one = (Component: ComponentType): BlockExampleVariant[] => [{ Component }];
const tappable = (Component: ComponentType): BlockExampleVariant[] => [
  { Component, interactive: true },
];

export const BLOCK_EXAMPLES: Record<ContentBlockType, ReadonlyArray<BlockExampleVariant>> = {
  heading: [
    { caption: "Уровни 1–6", Component: HeadingLevelsExample },
    { caption: "На странице: H2 → H3 → H4", Component: HeadingPageExample },
  ],
  paragraph: one(ParagraphExample),
  callout: [
    { caption: "Стиль: Информация, Предупреждение, Успех, Ошибка", Component: CalloutExample },
  ],
  accordion: tappable(AccordionExample),
  steps: one(StepsExample),
  tabs: tappable(TabsExample),
  category_grid: [
    { caption: "Иконка · заливка · изображение категории", Component: CategoryGridExample },
  ],
  contact_list: one(ContactListExample),
  link: [
    { caption: "Вид: Кнопка", Component: LinkButtonExample },
    { caption: "Вид: Карточка", Component: LinkCardExample },
  ],
  file_list: [
    { caption: "Отображение: Файл для скачивания", Component: FileTileExample, interactive: true },
    { caption: "Отображение: Изображение в тексте", Component: FileInlineImageExample },
  ],
  form_action: one(FormActionExample),
  form_catalog: one(FormCatalogExample),
  submission_history: one(SubmissionHistoryExample),
  test_action: one(TestActionExample),
  test_catalog: one(TestCatalogExample),
  test_attempt_history: one(TestAttemptHistoryExample),
  faq_list: tappable(FaqListExample),
  news_list: one(NewsListExample),
  capability_action: one(CapabilityActionExample),
};

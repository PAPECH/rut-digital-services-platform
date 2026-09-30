import type {
  ContentBlock,
  ContentBlockType,
  NestedContentBlock,
  NestedContentBlockType,
} from "@/entities/content/model/types";

export const blockLabels: Record<ContentBlockType, string> = {
  heading: "Заголовок",
  paragraph: "Текст",
  callout: "Плашка",
  contact_list: "Контакты",
  accordion: "Аккордеон",
  steps: "Шаги",
  link: "Ссылка",
  file_list: "Файлы",
  form_action: "Переход к форме",
  test_action: "Переход к тесту",
  capability_action: "Подключаемая возможность",
  form_catalog: "Список доступных форм",
  test_catalog: "Список доступных тестов",
  submission_history: "История заявок пользователя",
  test_attempt_history: "История прохождения тестов",
  faq_list: "Частые вопросы (FAQ)",
  news_list: "Новости",
  category_grid: "Сетка категорий",
  tabs: "Вкладки",
};

function stableId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`;
}

export function createNestedBlock(
  type: NestedContentBlockType,
): NestedContentBlock {
  const id = stableId(type);
  switch (type) {
    case "heading":
      return { id, type, text: "Новый заголовок", level: 2 };
    case "paragraph":
      return { id, type, text: "Новый текстовый блок" };
    case "callout":
      return { id, type, title: null, text: "Важная информация", tone: "info" };
    case "contact_list":
      return { id, type, items: [{ label: "Телефон", value: "", href: null }] };
    case "accordion":
      return {
        id,
        type,
        items: [{ id: stableId("item"), title: "Раздел", text: "Содержимое" }],
      };
    case "steps":
      return {
        id,
        type,
        items: [
          { id: stableId("step"), title: "Шаг 1", text: "Описание действия" },
        ],
      };
    case "link":
      return {
        id,
        type,
        title: "Открыть ссылку",
        href: "https://",
        style: "button",
        external: true,
      };
    case "file_list":
      return {
        id,
        type,
        items: [{ attachment_id: 0, title: "Документ", description: null, display_mode: "tile" }],
      };
    case "form_action":
      return {
        id,
        type,
        form_id: 0,
        title: "Заполнить форму",
        description: null,
      };
    case "test_action":
      return {
        id,
        type,
        test_id: 0,
        title: "Пройти тест",
        description: null,
      };
    case "capability_action":
      return {
        id,
        type,
        capability_key: "request_status",
        view_key: "lookup",
        title: "Открыть сервис",
        description: null,
      };
  }
}

export function createBlock(type: ContentBlockType): ContentBlock {
  switch (type) {
    case "tabs":
      return {
        id: stableId("tabs"),
        type: "tabs",
        tabs: [
          { key: stableId("tab").toLowerCase(), title: "Вкладка", blocks: [] },
        ],
      };
    case "category_grid":
      return {
        id: stableId("category_grid"),
        type,
        parent_id: null,
        title: null,
      };
    case "form_catalog":
      return {
        id: stableId("form_catalog"),
        type,
        title: "Доступные формы",
      };
    case "test_catalog":
      return {
        id: stableId("test_catalog"),
        type,
        title: "Доступные тесты",
      };
    case "submission_history":
      return {
        id: stableId("submission_history"),
        type,
        title: "История заявок",
      };
    case "test_attempt_history":
      return {
        id: stableId("test_attempt_history"),
        type,
        title: "История прохождения тестов",
      };
    case "faq_list":
      return {
        id: stableId("faq_list"),
        type,
        title: "Частые вопросы",
      };
    case "news_list":
      return {
        id: stableId("news_list"),
        type,
        title: "Новости",
      };
    default:
      return createNestedBlock(type);
  }
}

export function createItemId(prefix: string): string {
  return stableId(prefix);
}

import type { FormField, FormFieldType, FormOption } from "@/entities/form/model/types";
import { createFormField } from "@/features/form-management/lib/fieldFactory";

/**
 * One entry per form field type (Task 087). A full `Record`, so a new field type fails the
 * type-check until it is described here. Samples are built with the builder's own
 * `createFormField`, then rendered by the builder's own preview registry.
 */
export interface FieldGuideEntry {
  use: string;
  sample: Partial<FormField> & { label: string };
}

const options = (...labels: string[]): FormOption[] =>
  labels.map((label, index) => ({ value: `option_${index + 1}`, label }));

export const FIELD_GUIDE: Record<FormFieldType, FieldGuideEntry> = {
  short_text: {
    use: "Короткий ответ в одну строку: номер комнаты, номер группы, название.",
    sample: { label: "Номер комнаты", required: true },
  },
  long_text: {
    use: "Развёрнутый ответ: описание проблемы, комментарий, предложение.",
    sample: { label: "Опишите проблему", help_text: "Что сломалось и с какого времени" },
  },
  email: {
    use: "Адрес почты с проверкой формата. Почту пользователя из профиля заново не спрашивайте.",
    sample: { label: "Почта для ответа от деканата" },
  },
  phone: {
    use: "Номер телефона с проверкой формата — например, контакт родителя.",
    sample: { label: "Телефон родителя" },
  },
  number: {
    use: "Число с ограничениями «от» и «до»: количество, сумма, курс.",
    sample: { label: "Сколько экземпляров справки нужно", required: true },
  },
  date: {
    use: "Выбор даты в календаре: дата заезда, дата события.",
    sample: { label: "Желаемая дата заселения" },
  },
  checkbox: {
    use: "Одна галочка «да / нет»: согласие, подтверждение.",
    sample: { label: "Подтверждаю, что ознакомлен с правилами проживания", required: true },
  },
  select: {
    use: "Один вариант из длинного списка (больше 5) — компактный выпадающий список.",
    sample: {
      label: "Общежитие",
      options: options("Общежитие № 1", "Общежитие № 2", "Общежитие № 3", "Комплекс № 3"),
    },
  },
  radio: {
    use: "Один вариант из короткого списка (до 5) — все варианты видны сразу.",
    sample: { label: "Форма обучения", options: options("Очная", "Заочная", "Очно-заочная") },
  },
  multiselect: {
    use: "Несколько вариантов сразу; можно задать минимум и максимум выбранных.",
    sample: {
      label: "Что нужно отремонтировать",
      options: options("Мебель", "Сантехника", "Электрика"),
    },
  },
  file: {
    use: "Загрузка файлов: скан, фото. Можно ограничить типы, число и размер файлов.",
    sample: {
      label: "Фото поломки",
      help_text: "Сфотографируйте поломку",
      max_files: 3,
      accepted_mime_types: ["image/jpeg", "image/png"],
    },
  },
};

export function sampleField(type: FormFieldType): FormField {
  return { ...createFormField(type), ...FIELD_GUIDE[type].sample } as FormField;
}

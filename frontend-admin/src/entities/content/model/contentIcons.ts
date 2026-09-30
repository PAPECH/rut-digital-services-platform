export const CONTENT_ICONS = [
  { value: 'folder', label: 'Папка' },
  { value: 'document', label: 'Документ' },
  { value: 'info', label: 'Информация' },
  { value: 'star', label: 'Важное' },
  { value: 'contact', label: 'Контакты' },
  { value: 'building', label: 'Организация' },
  { value: 'calendar', label: 'Календарь' },
  { value: 'book', label: 'Книга' },
  { value: 'map', label: 'Карта' },
  { value: 'users', label: 'Люди' },
  { value: 'briefcase', label: 'Работа' },
  { value: 'help-circle', label: 'Помощь' },
  { value: 'mail', label: 'Почта' },
  { value: 'phone', label: 'Телефон' },
  { value: 'clock', label: 'Время' },
  { value: 'lock', label: 'Доступ' },
  { value: 'settings', label: 'Настройки' },
  { value: 'bell', label: 'Уведомления' },
  { value: 'file-text', label: 'Файл' },
  { value: 'check', label: 'Готово' },
  { value: 'alert-circle', label: 'Внимание' },
  { value: 'link', label: 'Ссылка' },
] as const

export type ContentIconName = (typeof CONTENT_ICONS)[number]['value']

export function isContentIconName(value: string): value is ContentIconName {
  return CONTENT_ICONS.some((icon) => icon.value === value)
}

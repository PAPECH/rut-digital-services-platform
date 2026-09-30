export const CONTENT_ICON_NAMES = [
  'folder',
  'document',
  'info',
  'star',
  'contact',
  'building',
  'calendar',
  'book',
  'map',
  'users',
  'briefcase',
  'help-circle',
  'mail',
  'phone',
  'clock',
  'lock',
  'settings',
  'bell',
  'file-text',
  'check',
  'alert-circle',
  'link',
] as const

export type ContentIconName = (typeof CONTENT_ICON_NAMES)[number]

export function isContentIconName(value: string): value is ContentIconName {
  return CONTENT_ICON_NAMES.some((icon) => icon === value)
}

import { isContentIconName, type ContentIconName } from '@/entities/content/model/contentIcons'

const PATHS: Record<ContentIconName, string> = {
  folder: 'M3 6h7l2 2h9v11H3z',
  document: 'M6 3h8l4 4v14H6zM14 3v5h5M9 12h6M9 16h6',
  info: 'M12 11v6M12 7h.01M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  star: 'M12 2l3 7 7 1-5.5 5 1.5 7-6-3.5L6 22l1.5-7L2 10l7-1 3-7z',
  contact: 'M4 3h16v18H4zM8 3v18M11 8h5M11 12h5M11 16h3',
  building: 'M4 21V5h8v16M12 9h8v12M3 21h18M8 9h.01M8 13h.01M8 17h.01M16 13h.01M16 17h.01',
  calendar: 'M4 5h16v16H4zM4 9h16M8 3v4M16 3v4',
  book: 'M4 4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22.5V4.5z',
  map: 'M9 20l-6 2V6l6-2 6 2 6-2v16l-6 2-6-2zM9 4v16M15 6v16',
  users: 'M9 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21a7 7 0 0 1 14 0M17 8a3 3 0 1 1 0 6M22 21a6 6 0 0 0-5-6',
  briefcase: 'M3 8h18v12H3zM8 8V5h8v3M3 13h18',
  'help-circle': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2 2-2 3.5M12 17h.01',
  mail: 'M3 5h18v14H3zM3 7l9 6 9-6',
  phone:
    'M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2a1.5 1.5 0 0 1 1.5-.4c1.1.4 2.3.6 3.6.6a1.5 1.5 0 0 1 1.5 1.5V21a1.5 1.5 0 0 1-1.5 1.5C10.6 22.5 1.5 13.4 1.5 2.5A1.5 1.5 0 0 1 3 1h3.1a1.5 1.5 0 0 1 1.5 1.5c0 1.3.2 2.5.6 3.6a1.5 1.5 0 0 1-.4 1.5L6.6 10.8z',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 3',
  lock: 'M4 11h16v10H4zM8 11V7a4 4 0 0 1 8 0v4',
  settings:
    'M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8L4.2 7a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.1.6.5 1.2 1.5 1.4H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
  bell: 'M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9zM10 21a2 2 0 0 0 4 0',
  'file-text': 'M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM14 2v5h5M8 12h8M8 16h5',
  check: 'M5 12l5 5L20 7',
  'alert-circle': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7.5v6M12 16.5v.01',
  link: 'M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1-1',
}

export function ContentIcon({ name }: { name: string }) {
  const normalized = isContentIconName(name) ? name : 'folder'
  return (
    <svg
      viewBox='0 0 24 24'
      fill='none'
      stroke='currentColor'
      strokeWidth='1.8'
      strokeLinecap='round'
      strokeLinejoin='round'>
      <path d={PATHS[normalized]} />
    </svg>
  )
}

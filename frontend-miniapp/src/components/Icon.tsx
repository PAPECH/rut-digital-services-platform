type SVGProps = React.SVGProps<SVGSVGElement>

const stroke: SVGProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  viewBox: '0 0 24 24',
}

export const Icon = {
  Dashboard: () => (
    <svg {...stroke}>
      <rect x='3' y='3' width='7' height='9' rx='2' />
      <rect x='14' y='3' width='7' height='5' rx='2' />
      <rect x='14' y='12' width='7' height='9' rx='2' />
      <rect x='3' y='16' width='7' height='5' rx='2' />
    </svg>
  ),
  Forms: () => (
    <svg {...stroke}>
      <rect x='4' y='3' width='16' height='18' rx='2' />
      <path d='M8 8h8M8 12h8M8 16h5' />
    </svg>
  ),
  Tickets: () => (
    <svg {...stroke}>
      <path d='M21 10a2 2 0 0 1-2-2V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v1a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a2 2 0 0 1 2-2z' />
      <path d='M12 5v14' strokeDasharray='2 3' />
    </svg>
  ),
  Users: () => (
    <svg {...stroke}>
      <circle cx='9' cy='8' r='3' />
      <path d='M3 20c0-3 3-5 6-5s6 2 6 5' />
      <circle cx='17' cy='10' r='2.5' />
      <path d='M14 19c0-2 1.5-3.5 4-3.5s3 1.5 3 3.5' />
    </svg>
  ),
  Builder: () => (
    <svg {...stroke}>
      <path d='M3 7h18M3 12h18M3 17h12' />
      <circle cx='19' cy='17' r='2' />
    </svg>
  ),
  Search: () => (
    <svg {...stroke}>
      <circle cx='11' cy='11' r='7' />
      <path d='m20 20-3.5-3.5' />
    </svg>
  ),
  Bell: () => (
    <svg {...stroke}>
      <path d='M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9Z' />
      <path d='M10 21a2 2 0 0 0 4 0' />
    </svg>
  ),
  Settings: () => (
    <svg {...stroke}>
      <circle cx='12' cy='12' r='3' />
      <path d='M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8L4.2 7a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.1.6.5 1.2 1.5 1.4H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z' />
    </svg>
  ),
  ChevronDown: () => (
    <svg {...stroke}>
      <path d='m6 9 6 6 6-6' />
    </svg>
  ),
  X: () => (
    <svg {...stroke}>
      <path d='M18 6 6 18M6 6l12 12' />
    </svg>
  ),
  Plus: () => (
    <svg {...stroke}>
      <path d='M12 5v14M5 12h14' />
    </svg>
  ),
  Edit: () => (
    <svg {...stroke}>
      <path d='M14 4l6 6-12 12H2v-6L14 4Z' />
    </svg>
  ),
  Trash: () => (
    <svg {...stroke}>
      <path d='M4 7h16M10 11v6M14 11v6M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13M9 7V4h6v3' />
    </svg>
  ),
  Check: () => (
    <svg {...stroke}>
      <path d='m5 12 5 5L20 7' />
    </svg>
  ),
  Filter: () => (
    <svg {...stroke}>
      <path d='M4 5h16l-6 8v5l-4 2v-7L4 5Z' />
    </svg>
  ),
  Send: () => (
    <svg {...stroke}>
      <path d='M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z' />
    </svg>
  ),
  Paperclip: () => (
    <svg {...stroke}>
      <path d='M21 12 12 21a5 5 0 0 1-7-7L14 5a3.5 3.5 0 1 1 5 5l-9 9a2 2 0 0 1-3-3l8-8' />
    </svg>
  ),
  Download: () => (
    <svg {...stroke}>
      <path d='M12 3v12M7 10l5 5 5-5M5 21h14' />
    </svg>
  ),
  Logout: () => (
    <svg {...stroke}>
      <path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9' />
    </svg>
  ),
  Menu: () => (
    <svg {...stroke}>
      <path d='M4 7h16M4 12h16M4 17h16' />
    </svg>
  ),
  Calendar: () => (
    <svg {...stroke}>
      <rect x='3' y='4' width='18' height='17' rx='2' />
      <path d='M16 2v4M8 2v4M3 10h18' />
    </svg>
  ),
  Clock: () => (
    <svg {...stroke}>
      <circle cx='12' cy='12' r='9' />
      <path d='M12 7v5l3 3' />
    </svg>
  ),
  Mail: () => (
    <svg {...stroke}>
      <rect x='3' y='5' width='18' height='14' rx='2' />
      <path d='m3 7 9 6 9-6' />
    </svg>
  ),
  Phone: () => (
    <svg {...stroke}>
      <path d='M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2a1.5 1.5 0 0 1 1.5-.4c1.1.4 2.3.6 3.6.6a1.5 1.5 0 0 1 1.5 1.5V21a1.5 1.5 0 0 1-1.5 1.5C10.6 22.5 1.5 13.4 1.5 2.5A1.5 1.5 0 0 1 3 1h3.1a1.5 1.5 0 0 1 1.5 1.5c0 1.3.2 2.5.6 3.6a1.5 1.5 0 0 1-.4 1.5L6.6 10.8Z' />
    </svg>
  ),
  Eye: () => (
    <svg {...stroke}>
      <path d='M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z' />
      <circle cx='12' cy='12' r='3' />
    </svg>
  ),
  EyeOff: () => (
    <svg {...stroke}>
      <path d='M3 3l18 18' />
      <path d='M10.6 5.2A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a17.5 17.5 0 0 1-3.2 4.1M6.5 6.6C4 8.2 2 12 2 12s3.5 7 10 7c1.3 0 2.5-.2 3.6-.7' />
      <path d='M9.9 9.9a3 3 0 0 0 4.2 4.2' />
    </svg>
  ),
  Copy: () => (
    <svg {...stroke}>
      <rect x='9' y='9' width='12' height='12' rx='2' />
      <path d='M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1' />
    </svg>
  ),
  ExternalLink: () => (
    <svg {...stroke}>
      <path d='M14 3h7v7M21 3l-9 9' />
      <path d='M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6' />
    </svg>
  ),
  ArrowLeft: () => (
    <svg {...stroke}>
      <path d='M19 12H5M11 6l-6 6 6 6' />
    </svg>
  ),
  ArrowRight: () => (
    <svg {...stroke}>
      <path d='M5 12h14M13 6l6 6-6 6' />
    </svg>
  ),
  ChevronLeft: () => (
    <svg {...stroke}>
      <path d='m15 6-6 6 6 6' />
    </svg>
  ),
  ChevronRight: () => (
    <svg {...stroke}>
      <path d='m9 6 6 6-6 6' />
    </svg>
  ),
  ChevronUp: () => (
    <svg {...stroke}>
      <path d='m6 15 6-6 6 6' />
    </svg>
  ),
  Info: () => (
    <svg {...stroke}>
      <circle cx='12' cy='12' r='9' />
      <path d='M12 11v6M12 7.5v.01' />
    </svg>
  ),
  AlertCircle: () => (
    <svg {...stroke}>
      <circle cx='12' cy='12' r='9' />
      <path d='M12 7.5v6M12 16.5v.01' />
    </svg>
  ),
  Star: () => (
    <svg {...stroke}>
      <path d='m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21l1.2-6.9-5-4.9 6.9-1L12 2Z' />
    </svg>
  ),
  Lock: () => (
    <svg {...stroke}>
      <rect x='4' y='11' width='16' height='10' rx='2' />
      <path d='M8 11V7a4 4 0 0 1 8 0v4' />
    </svg>
  ),
  User: () => (
    <svg {...stroke}>
      <circle cx='12' cy='8' r='4' />
      <path d='M4 21c0-4 3.5-7 8-7s8 3 8 7' />
    </svg>
  ),
  Refresh: () => (
    <svg {...stroke}>
      <path d='M21 12a9 9 0 1 1-3-6.7' />
      <path d='M21 3v6h-6' />
    </svg>
  ),
  FileText: () => (
    <svg {...stroke}>
      <path d='M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z' />
      <path d='M14 2v5h5M8 12h8M8 16h5' />
    </svg>
  ),
  Upload: () => (
    <svg {...stroke}>
      <path d='M12 21V9M7 14l5-5 5 5M5 21h14' />
    </svg>
  ),
  MoreVertical: () => (
    <svg {...stroke}>
      <circle cx='12' cy='5' r='1.2' />
      <circle cx='12' cy='12' r='1.2' />
      <circle cx='12' cy='19' r='1.2' />
    </svg>
  ),
  Folder: () => (
    <svg {...stroke}>
      <path d='M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z' />
    </svg>
  ),
  Document: () => (
    <svg {...stroke}>
      <path d='M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z' />
      <path d='M14 2v5h5M8 12h8M8 16h5' />
    </svg>
  ),
  Contact: () => (
    <svg {...stroke}>
      <rect x='3' y='4' width='18' height='16' rx='2' />
      <circle cx='9' cy='10' r='2.5' />
      <path d='M6 17c0-2 1.5-3.5 3-3.5s3 1.5 3 3.5M14 9h5M14 13h5' />
    </svg>
  ),
  Building: () => (
    <svg {...stroke}>
      <rect x='4' y='3' width='10' height='18' rx='1' />
      <rect x='14' y='9' width='6' height='12' rx='1' />
      <path d='M7 7h1M11 7h1M7 11h1M11 11h1M7 15h1M11 15h1M17 13h1M17 17h1' />
    </svg>
  ),
  Book: () => (
    <svg {...stroke}>
      <path d='M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5v-17Z' />
      <path d='M4 19.5A2.5 2.5 0 0 1 6.5 17H20' />
    </svg>
  ),
  Map: () => (
    <svg {...stroke}>
      <path d='M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z' />
      <path d='M9 4v14M15 6v14' />
    </svg>
  ),
  Briefcase: () => (
    <svg {...stroke}>
      <rect x='2' y='7' width='20' height='13' rx='2' />
      <path d='M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M2 12h20' />
    </svg>
  ),
  HelpCircle: () => (
    <svg {...stroke}>
      <circle cx='12' cy='12' r='9' />
      <path d='M9.5 9a2.5 2.5 0 0 1 4.8 1c0 1.5-2.3 2-2.3 3.5' />
      <path d='M12 17v.01' />
    </svg>
  ),
  Home: () => (
    <svg {...stroke}>
      <path d='M3 11l9-8 9 8' />
      <path d='M5 10v10h14V10' />
      <path d='M9 20v-6h6v6' />
    </svg>
  ),
  Profile: () => (
    <svg {...stroke}>
      <circle cx='12' cy='8' r='4' />
      <path d='M4 21c0-4 3.5-7 8-7s8 3 8 7' />
    </svg>
  ),
  History: () => (
    <svg {...stroke}>
      <path d='M3 12a9 9 0 1 0 3-6.7' />
      <path d='M3 3v5h5' />
      <path d='M12 7v5l4 2' />
    </svg>
  ),
}

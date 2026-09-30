import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

type Lang = 'ru' | 'en'
type Dict = Record<string, string>

const DICT: Record<Lang, Dict> = {
  ru: {
    'brand.name': 'УЦТ',
    'brand.sub': 'РУТ МИИТ',
    'nav.dashboard': 'Дашборд',
    'nav.submissions': 'Заявки',
    'nav.tickets': 'Тикеты',
    'nav.users': 'Пользователи',
    'nav.builder': 'Конструктор форм',
    'nav.admins': 'Сотрудники',
    'nav.bot_settings': 'Настройки бота',
    'nav.faq': 'FAQ',
    'nav.kb': 'База знаний',
    'role.admin': 'Админ',
    'role.employee': 'Сотрудник',
    'action.logout': 'Выйти',
    'action.save': 'Сохранить',
    'action.cancel': 'Отмена',
    'action.delete': 'Удалить',
    'action.edit': 'Изменить',
    'action.add': 'Добавить',
    'action.send': 'Отправить',
    'action.open': 'Открыть',
    'common.loading': 'Загрузка…',
    'common.empty': 'Ничего не найдено',
    'common.search': 'Поиск…',
    'status.new': 'Новая',
    'status.in_work': 'В работе',
    'status.done': 'Завершено',
    'status.rejected': 'Отклонено',

    'page.dashboard.title': 'Дашборд',
    'page.dashboard.sub': 'Сводка по обращениям и заявкам',
    'page.dashboard.week': 'Неделя',
    'page.dashboard.month': 'Месяц',
    'page.dashboard.quarter': 'Квартал',
    'page.dashboard.tickets_by_days': 'Заявок по дням',
    'page.dashboard.tickets_by_type': 'По типам справок',
    'page.dashboard.of_n_days': 'за {{days}} дн.',
    'page.dashboard.total_submissions': 'Всего заявок',
    'page.dashboard.avg_time_to_work': 'Среднее время до взятия в работу',
    'page.dashboard.avg_time_to_done': 'Среднее время до завершения',
    'page.dashboard.rejected_share': 'Доля отклонённых',
    'page.dashboard.new_users': 'Новых пользователей',
    'page.dashboard.users_with_submission': 'Из них подали заявку',
    'page.dashboard.conversion_rate': 'Конверсия в подачу',
    'page.dashboard.conversion_rate_sub': 'пользователь → заявка',

    'page.submissions.title': 'Заявки',
    'page.submissions.sub': 'Заполненные формы студентов',
    'page.tickets.title': 'Тикеты',
    'page.tickets.sub': 'Обращения студентов в реальном времени',
    'page.users.title': 'Пользователи',
    'page.users.sub': 'Пользователей бота',
    'page.builder.title': 'Конструктор форм',
    'page.builder.sub': 'Создание и настройка шаблонов справок',
    'page.admins.title': 'Сотрудники',
    'page.admins.sub': 'Управление доступом сотрудников и админов',
    'page.bot_settings.title': 'Настройки бота',
    'page.bot_settings.sub': 'Тексты приветствия бота на русском и английском',
    'push.enable': 'Включить уведомления о новых тикетах',
    'push.disable': 'Выключить уведомления',
    'push.title': 'Новое обращение',
  },
  en: {
    'brand.name': 'MFC',
    'brand.sub': 'RUT MIIT',
    'nav.dashboard': 'Dashboard',
    'nav.submissions': 'Applications',
    'nav.tickets': 'Tickets',
    'nav.users': 'Users',
    'nav.builder': 'Form builder',
    'nav.admins': 'Staff',
    'nav.bot_settings': 'Bot settings',
    'nav.faq': 'FAQ',
    'nav.kb': 'Knowledge base',
    'role.admin': 'Admin',
    'role.employee': 'Employee',
    'action.logout': 'Log out',
    'action.save': 'Save',
    'action.cancel': 'Cancel',
    'action.delete': 'Delete',
    'action.edit': 'Edit',
    'action.add': 'Add',
    'action.send': 'Send',
    'action.open': 'Open',
    'common.loading': 'Loading…',
    'common.empty': 'Nothing found',
    'common.search': 'Search…',
    'status.new': 'New',
    'status.in_work': 'In progress',
    'status.done': 'Done',
    'status.rejected': 'Rejected',
    'page.dashboard.title': 'Dashboard',
    'page.dashboard.sub': 'MFC tickets and applications overview',
    'page.dashboard.week': 'Week',
    'page.dashboard.month': 'Month',
    'page.dashboard.quarter': 'Quarter',
    'page.dashboard.tickets_by_days': 'Tickets by days',
    'page.dashboard.tickets_by_type': 'By certificate types',
    'page.dashboard.of_n_days': 'of {{days}} days',
    'page.dashboard.total_submissions': 'Total submissions',
    'page.dashboard.avg_time_to_work': 'Avg. time to start processing',
    'page.dashboard.avg_time_to_done': 'Avg. time to completion',
    'page.dashboard.rejected_share': 'Share of rejected',
    'page.dashboard.new_users': 'New users',
    'page.dashboard.users_with_submission': 'Users with submission',
    'page.dashboard.conversion_rate': 'Conversion rate',

    'page.submissions.title': 'Applications',
    'page.submissions.sub': 'Forms submitted by students',
    'page.tickets.title': 'Tickets',
    'page.tickets.sub': 'Student conversations in real time',
    'page.users.title': 'Users',
    'page.users.sub': 'Students who contacted the MFC',
    'page.builder.title': 'Form builder',
    'page.builder.sub': 'Create and configure certificate templates',
    'page.admins.title': 'Staff',
    'page.admins.sub': 'Manage employee and admin access',
    'page.bot_settings.title': 'Bot settings',
    'page.bot_settings.sub': 'Welcome message for the bot, in Russian and English',
    'push.enable': 'Enable notifications for new tickets',
    'push.disable': 'Disable notifications',
    'push.title': 'New MFC inquiry',
  },
}

const LS_KEY = 'mfc.admin.lang'

function detectInitial(): Lang {
  const saved = (localStorage.getItem(LS_KEY) || '').toLowerCase()
  if (saved === 'ru' || saved === 'en') return saved
  const nav = (navigator.language || '').toLowerCase()
  return nav.startsWith('ru') ? 'ru' : 'en'
}

interface I18nState {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const Ctx = createContext<I18nState | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectInitial)

  useEffect(() => {
    localStorage.setItem(LS_KEY, lang)
    document.documentElement.lang = lang
  }, [lang])

  const setLang = useCallback((l: Lang) => setLangState(l), [])
  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      let str = DICT[lang][key] ?? DICT.ru[key] ?? key
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          str = str.replace(new RegExp(`{{${k}}}`, 'g'), String(v))
        })
      }
      return str
    },
    [lang],
  )
  const value = useMemo<I18nState>(() => ({ lang, setLang, t }), [lang, setLang, t])
  return createElement(Ctx.Provider, { value }, children)
}

export function useI18n(): I18nState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useI18n must be used within I18nProvider')
  return v
}

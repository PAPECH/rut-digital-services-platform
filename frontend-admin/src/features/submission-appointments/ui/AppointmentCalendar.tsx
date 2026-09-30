import { useMemo, useState } from 'react'

import * as styles from './AppointmentCalendar.css'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function parseDate(value: string): Date {
  return new Date(`${value}T00:00:00Z`)
}

function dateKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function monthKey(date: Date): string {
  return date.toISOString().slice(0, 7)
}

function startOfMonth(value: string): Date {
  const date = parseDate(value)
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1))
}

function shiftMonth(date: Date, amount: number): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + amount, 1))
}

function monthDays(month: Date): Array<{ date: string; day: number; inMonth: boolean }> {
  const first = new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth(), 1))
  const mondayOffset = (first.getUTCDay() + 6) % 7
  const cursor = new Date(first)
  cursor.setUTCDate(cursor.getUTCDate() - mondayOffset)

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(cursor)
    date.setUTCDate(date.getUTCDate() + index)
    return {
      date: dateKey(date),
      day: date.getUTCDate(),
      inMonth: date.getUTCMonth() === month.getUTCMonth(),
    }
  })
}

function monthLabel(date: Date): string {
  return new Intl.DateTimeFormat('ru-RU', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

export function AppointmentCalendar({
  dates,
  value,
  fullyBookedDates,
  disabled,
  onChange,
}: {
  dates: string[]
  value: string
  fullyBookedDates: Set<string>
  disabled: boolean
  onChange: (date: string) => void
}) {
  const firstMonth = startOfMonth(dates[0])
  const lastMonth = startOfMonth(dates[dates.length - 1])
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(value))
  const availableDates = useMemo(() => new Set(dates), [dates])
  const cells = useMemo(() => monthDays(visibleMonth), [visibleMonth])
  const canGoBack = monthKey(visibleMonth) > monthKey(firstMonth)
  const canGoForward = monthKey(visibleMonth) < monthKey(lastMonth)

  return (
    <div className={styles.calendar} aria-label='Календарь дат приёма'>
      <div className={styles.header}>
        <button
          type='button'
          className={styles.navigationButton}
          disabled={disabled || !canGoBack}
          aria-label='Предыдущий месяц'
          onClick={() => setVisibleMonth((month) => shiftMonth(month, -1))}>
          ‹
        </button>
        <strong className={styles.monthTitle}>{monthLabel(visibleMonth)}</strong>
        <button
          type='button'
          className={styles.navigationButton}
          disabled={disabled || !canGoForward}
          aria-label='Следующий месяц'
          onClick={() => setVisibleMonth((month) => shiftMonth(month, 1))}>
          ›
        </button>
      </div>

      <div className={styles.weekdays} aria-hidden='true'>
        {WEEKDAYS.map((weekday) => (
          <span className={styles.weekday} key={weekday}>{weekday}</span>
        ))}
      </div>

      <div className={styles.days}>
        {cells.map((cell) => {
          const isAvailable = cell.inMonth && availableDates.has(cell.date)
          const isFullyBooked = isAvailable && fullyBookedDates.has(cell.date)
          const isSelected = cell.date === value
          const className = [
            styles.day,
            !cell.inMonth ? styles.dayOutside : '',
            isAvailable && !isFullyBooked ? styles.dayAvailable : '',
            isSelected ? styles.daySelected : '',
            isFullyBooked ? styles.dayFullyBooked : '',
          ].filter(Boolean).join(' ')

          return (
            <button
              type='button'
              className={className}
              key={cell.date}
              disabled={disabled || !isAvailable || isFullyBooked}
              aria-label={isFullyBooked ? `${cell.date}: мест нет` : cell.date}
              aria-pressed={isSelected}
              onClick={() => onChange(cell.date)}>
              {cell.inMonth ? cell.day : ''}
            </button>
          )
        })}
      </div>

      <div className={styles.legend} aria-label='Обозначения календаря'>
        <span className={styles.legendItem}>
          <i className={`${styles.legendDot} ${styles.legendDotAvailable}`} /> доступно
        </span>
        <span className={styles.legendItem}>
          <i className={`${styles.legendDot} ${styles.legendDotSelected}`} /> выбрано
        </span>
        <span className={styles.legendItem}>
          <i className={styles.legendDot} /> недоступно
        </span>
      </div>
    </div>
  )
}


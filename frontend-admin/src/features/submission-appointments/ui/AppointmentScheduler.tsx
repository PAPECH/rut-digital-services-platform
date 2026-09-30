import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from '@/api/client'
import type { Submission, SubmissionAppointmentSlot } from '@/api/types'
import { AppointmentCalendar } from './AppointmentCalendar'

const SLOT_LABELS = ['10:00', '10:15', '10:30', '10:45', '11:00', '11:15', '11:30', '11:45']
const LOCATION = 'Главный корпус РУТ (МИИТ), кабинет 1201'

function moscowToday(): Date {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Moscow',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return new Date(Date.UTC(Number(value.year), Number(value.month) - 1, Number(value.day)))
}

function dateKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function nextThursdays(count: number): string[] {
  const cursor = moscowToday()
  while (cursor.getUTCDay() !== 4) cursor.setUTCDate(cursor.getUTCDate() + 1)
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(cursor)
    date.setUTCDate(date.getUTCDate() + index * 7)
    return dateKey(date)
  })
}

function slotIso(date: string, label: string): string {
  return `${date}T${label}:00+03:00`
}

function slotKey(value: string): number {
  return new Date(value).getTime()
}

function formatDate(date: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${date}T00:00:00Z`))
}

export function AppointmentScheduler({
  submission,
  onBooked,
}: {
  submission: Submission
  onBooked: (updated: Submission) => void
}) {
  const dates = useMemo(() => nextThursdays(8), [])
  const [activeDate, setActiveDate] = useState(dates[0])
  const [occupied, setOccupied] = useState<SubmissionAppointmentSlot[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSlots = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await api.get<SubmissionAppointmentSlot[]>(
        `/submissions/appointments/slots?date_from=${dates[0]}&date_to=${dates[dates.length - 1]}`,
      )
      setOccupied(rows)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Не удалось загрузить расписание')
    } finally {
      setLoading(false)
    }
  }, [dates])

  useEffect(() => {
    void loadSlots()
  }, [loadSlots])

  useEffect(() => setSelected([]), [activeDate])

  const occupiedKeys = useMemo(() => new Set(occupied.map((slot) => slotKey(slot.starts_at))), [occupied])
  const fullyBookedDates = useMemo(
    () => new Set(
      dates.filter((date) => SLOT_LABELS.every((label) => occupiedKeys.has(slotKey(slotIso(date, label))))),
    ),
    [dates, occupiedKeys],
  )

  const toggleSlot = (index: number) => {
    setError(null)
    setSelected((current) => {
      if (current.includes(index)) return current.filter((value) => value !== index)
      if (current.length === 0) return [index]
      if (current.length === 1 && Math.abs(current[0] - index) === 1) {
        return [current[0], index].sort((a, b) => a - b)
      }
      return [index]
    })
  }

  const book = async () => {
    if (!selected.length) return
    setSaving(true)
    setError(null)
    try {
      const updated = await api.put<Submission>(`/submissions/${submission.id}/appointment`, {
        slot_starts: selected.map((index) => slotIso(activeDate, SLOT_LABELS[index])),
      })
      onBooked(updated)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Не удалось назначить встречу')
      await loadSlots()
    } finally {
      setSaving(false)
    }
  }

  const first = selected.length ? SLOT_LABELS[Math.min(...selected)] : null
  const lastIndex = selected.length ? Math.max(...selected) : null
  const end = lastIndex === null ? null : lastIndex === SLOT_LABELS.length - 1 ? '12:00' : SLOT_LABELS[lastIndex + 1]

  return (
    <section className='appointment-scheduler'>
      <div className='appointment-scheduler__head'>
        <div>
          <strong>Назначение встречи</strong>
          <span>Приём проводится по четвергам с 10:00 до 12:00</span>
        </div>
        <span className='tag neutral'>талон · 15 минут</span>
      </div>

      <div className='appointment-scheduler__date'>
        <span>Дата приёма</span>
        <AppointmentCalendar
          dates={dates}
          value={activeDate}
          fullyBookedDates={fullyBookedDates}
          disabled={loading || saving}
          onChange={setActiveDate}
        />
      </div>

      <div className='appointment-scheduler__slots' aria-label='Свободное время'>
        {SLOT_LABELS.map((label, index) => {
          const isOccupied = occupiedKeys.has(slotKey(slotIso(activeDate, label)))
          const isSelected = selected.includes(index)
          return (
            <button
              type='button'
              key={label}
              disabled={loading || saving || isOccupied}
              className={`${isSelected ? 'selected' : ''} ${isOccupied ? 'occupied' : ''}`}
              onClick={() => toggleSlot(index)}>
              <strong>{label}</strong>
              <span>{isOccupied ? 'занято' : isSelected ? 'выбрано' : 'свободно'}</span>
            </button>
          )
        })}
      </div>

      <div className='appointment-scheduler__details'>
        <div>
          <span>Место</span>
          <strong>{LOCATION}</strong>
        </div>
        <div>
          <span>Продолжительность</span>
          <strong>{selected.length ? `${selected.length * 15} минут` : 'Выберите 1–2 соседних талона'}</strong>
        </div>
      </div>

      {first && end ? (
        <p className='appointment-scheduler__summary'>
          Будет назначено: <strong>{formatDate(activeDate)}, {first}–{end}</strong>
        </p>
      ) : null}
      {error ? <p className='form-error'>{error}</p> : null}

      <button type='button' className='btn btn-primary' disabled={!selected.length || saving} onClick={() => void book()}>
        {saving ? 'Назначаем…' : 'Назначить встречу и завершить заявку'}
      </button>
    </section>
  )
}

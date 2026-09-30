import { useEffect, useMemo, useState } from 'react'

import { api } from '@/api/client'
import type { Profile, ProfileFieldDefinition } from '@/api/types'
import { useAuth } from '@/auth/AuthProvider'

export interface CoreProfileDraft {
  first_name: string
  last_name: string
  patronymic: string
  email: string
  birth_date: string
}

const emptyCore: CoreProfileDraft = {
  first_name: '',
  last_name: '',
  patronymic: '',
  email: '',
  birth_date: '',
}

function fieldValue(profile: Profile, key: string): unknown {
  const direct = (profile as unknown as Record<string, unknown>)[key]
  return direct ?? profile.local_data[key] ?? profile.shared_data[key] ?? ''
}

export function useProfileEditor(fields: ProfileFieldDefinition[]) {
  const { profile, refresh } = useAuth()
  const [core, setCore] = useState<CoreProfileDraft>(emptyCore)
  const [customData, setCustomData] = useState<Record<string, unknown>>({})
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!profile) return
    setCore({
      first_name: profile.first_name ?? '',
      last_name: profile.last_name ?? '',
      patronymic: profile.patronymic ?? '',
      email: profile.email ?? '',
      birth_date: profile.birth_date ?? '',
    })
    setCustomData(Object.fromEntries(fields.map((field) => [field.key, fieldValue(profile, field.key)])))
  }, [fields, profile])

  const canSave = useMemo(
    () =>
      !busy &&
      core.first_name.trim() !== '' &&
      core.last_name.trim() !== '' &&
      core.patronymic.trim() !== '' &&
      core.email.trim() !== '' &&
      core.birth_date !== '',
    [busy, core],
  )

  const save = async () => {
    setBusy(true)
    setMessage(null)
    try {
      await api.put('/profile', {
        ...core,
        birth_date: core.birth_date || null,
        custom_data: customData,
      })
      await refresh()
      setMessage('Сохранено ✓')
    } catch (error) {
      setMessage((error as Error)?.message ?? 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }

  return {
    core,
    setCore,
    customData,
    setCustomValue: (key: string, value: unknown) =>
      setCustomData((current) => ({ ...current, [key]: value })),
    busy,
    canSave,
    message,
    setMessage,
    save,
  }
}

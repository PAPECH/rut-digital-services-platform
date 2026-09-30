import type { Profile, ProfileFieldDefinition } from '@/api/types'

const coreRequirements = [
  ['last_name', 'Фамилия'],
  ['first_name', 'Имя'],
  ['patronymic', 'Отчество'],
  // ["email", "Электронная почта"],
  // ["birth_date", "Дата рождения"],
] as const

export function profileValue(profile: Profile, key: string): unknown {
  const direct = (profile as unknown as Record<string, unknown>)[key]
  if (direct !== undefined && direct !== null) return direct
  return profile.local_data[key] ?? profile.shared_data[key]
}

export function isMissing(value: unknown, requiresTrue = false): boolean {
  return (
    value === null ||
    value === undefined ||
    (typeof value === 'string' && !value.trim()) ||
    (requiresTrue && value !== true)
  )
}

export function getMissingProfileFields(
  profile: Profile | null | undefined,
  schema: ProfileFieldDefinition[] | undefined,
): string[] {
  if (!profile) return ['Профиль']
  const missing: string[] = coreRequirements
    .filter(([key]) => isMissing(profileValue(profile, key)))
    .map(([, label]) => label)
  if (isMissing(profile.phone) || !profile.phone_verified) {
    missing.push('Подтверждённый телефон')
  }
  missing.push(
    ...(schema ?? [])
      .filter((field) => field.required)
      .filter((field) => {
        const value = profileValue(profile, field.key)
        return isMissing(value, field.type === 'boolean')
      })
      .map((field) => field.label),
  )
  return [...new Set(missing)]
}

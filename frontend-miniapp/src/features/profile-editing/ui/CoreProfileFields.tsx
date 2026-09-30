import type { CoreProfileDraft } from '@/features/profile-editing/model/useProfileEditor'
import { useI18n } from '@/i18n'

export function CoreProfileFields({
  value,
  onChange,
}: {
  value: CoreProfileDraft
  onChange: (value: CoreProfileDraft) => void
}) {
  const { t } = useI18n()
  const set = (key: keyof CoreProfileDraft, next: string) => onChange({ ...value, [key]: next })

  return (
    <>
      <label className='field-label'>{t('services:form:last_name')} *</label>
      <input
        className='input'
        value={value.last_name}
        onChange={(event) => set('last_name', event.target.value)}
      />
      <label className='field-label profile-field-gap'>{t('services:form:first_name')} *</label>
      <input
        className='input'
        value={value.first_name}
        onChange={(event) => set('first_name', event.target.value)}
      />
      <label className='field-label profile-field-gap'>{t('services:form:patronymic')}</label>
      <input
        className='input'
        value={value.patronymic}
        onChange={(event) => set('patronymic', event.target.value)}
      />
      <label className='field-label profile-field-gap'>{t('services:form:email')} *</label>
      <input
        className='input'
        type='email'
        value={value.email}
        onChange={(event) => set('email', event.target.value)}
      />
      <label className='field-label profile-field-gap'>{t('services:form:birth_date')} *</label>
      <input
        className='input'
        type='date'
        value={value.birth_date}
        onChange={(event) => set('birth_date', event.target.value)}
      />
    </>
  )
}

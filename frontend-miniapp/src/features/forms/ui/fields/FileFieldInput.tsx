import { useState } from 'react'
import type { FieldInputProps, FileField, UploadedAttachment } from '@/entities/form/model/types'
import { formApi } from '@/features/forms/api/formApi'
import { FieldFrame } from './FieldFrame'
export function FileFieldInput({ field, value, onChange, disabled }: FieldInputProps<FileField>) {
  const [uploaded, setUploaded] = useState<UploadedAttachment[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ids = Array.isArray(value) ? (value as number[]) : []
  const upload = async (files: FileList | null) => {
    if (!files) return
    const selected = Array.from(files)
    if (ids.length + selected.length > field.max_files) {
      setError(`Можно прикрепить не больше ${field.max_files} файлов`)
      return
    }
    setBusy(true)
    setError(null)
    try {
      const next: UploadedAttachment[] = []
      for (const file of selected) {
        if (file.size > field.max_size_bytes) throw new Error(`Файл ${file.name} слишком большой`)
        if (field.accepted_mime_types.length && !field.accepted_mime_types.includes(file.type))
          throw new Error(`Тип файла ${file.name} не разрешён`)
        next.push(await formApi.upload(file))
      }
      setUploaded((current) => [...current, ...next])
      onChange([...ids, ...next.map((item) => item.id)])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить файл')
    } finally {
      setBusy(false)
    }
  }
  return (
    <FieldFrame field={field}>
      <label
        className={`input file-input ${disabled || busy || ids.length >= field.max_files ? 'file-input--disabled' : ''}`}>
        <input
          className='file-input__native'
          type='file'
          disabled={disabled || busy || ids.length >= field.max_files}
          multiple={field.max_files > 1}
          accept={field.accepted_mime_types.join(',') || undefined}
          onChange={(e) => void upload(e.target.files)}
        />
        <span className='file-input__label'>Выберите файл</span>
        <span className='file-input__name'>
          {ids.length > 0 ? `Загружено: ${ids.length}` : 'Файл не выбран'}
        </span>
      </label>
      {busy ? <small>Загрузка…</small> : null}
      {uploaded.map((file) => (
        <div className='row' key={file.id}>
          <span className='lbl'>{file.name}</span>
          <button
            className='btn btn-ghost btn-sm'
            type='button'
            onClick={() => {
              setUploaded((current) => current.filter((item) => item.id !== file.id))
              onChange(ids.filter((id) => id !== file.id))
            }}>
            Убрать
          </button>
        </div>
      ))}
      {error ? <div style={{ color: 'var(--st-rej-fg)', fontSize: 12 }}>{error}</div> : null}
    </FieldFrame>
  )
}

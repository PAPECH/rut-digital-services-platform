import { FilesBrowser } from '@/features/content-files/ui/FilesBrowser'

export function FilesPage() {
  return (
    <div className='page'>
      <div className='page-head'>
        <div>
          <h1 className='page-title'>Файлы бота</h1>
          <p className='page-sub'>Файлы, загруженные администраторами для карточек и блоков контента</p>
        </div>
      </div>

      <div className='card'>
        <div className='card-body'>
          <FilesBrowser />
        </div>
      </div>
    </div>
  )
}

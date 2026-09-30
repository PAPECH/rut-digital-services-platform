import { useState } from "react";

import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockPhoto } from "../../shared/MiniAppMock/MockPhoto";
import * as styles from "./FileBlockExamples.css";

/**
 * «Файл для скачивания»: a document shows a ↓ icon; an image shows a thumbnail that opens a
 * viewer, while tapping the title downloads it (`FileListBlockRenderer`).
 */
export function FileTileExample() {
  const [viewing, setViewing] = useState(false);
  return (
    <>
      <h3 className={mock.heading[3]}>Бланки для заполнения</h3>
      <div className={mock.fileItem}>
        <span className={mock.fileIcon} aria-hidden>
          ↓
        </span>
        <span className={mock.fileText}>
          <span className={mock.fileTitle}>Заявление на заселение</span>
          <span className={mock.fileDescription}>PDF · нажмите, чтобы скачать</span>
        </span>
      </div>
      <div className={mock.fileItem}>
        <button
          type="button"
          className={mock.fileThumbButton}
          aria-label="Открыть просмотр"
          onClick={() => setViewing(true)}
        >
          <MockPhoto />
        </button>
        <span className={mock.fileText}>
          <span className={mock.fileTitle}>Схема проезда</span>
          <span className={mock.fileDescription}>Миниатюра — просмотр, название — скачать</span>
        </span>
      </div>
      {viewing ? (
        <div className={styles.viewer}>
          <div className={styles.viewerHead}>
            Схема проезда
            <button type="button" className={styles.viewerClose} onClick={() => setViewing(false)}>
              ✕
            </button>
          </div>
          <MockPhoto className={styles.viewerImage} />
        </div>
      ) : (
        <span className={styles.hint}>Нажмите на миниатюру картинки</span>
      )}
    </>
  );
}

/** «Изображение в тексте»: the image itself, full width, no download row. */
export function FileInlineImageExample() {
  return (
    <>
      <p className={mock.paragraph}>Так выглядит комната в общежитии № 1:</p>
      <span className={mock.inlineImage}>
        <MockPhoto className={styles.inlineImage} />
      </span>
      <p className={mock.paragraph}>В каждой комнате — две кровати, стол и шкаф.</p>
    </>
  );
}

import type { FileField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
import * as styles from "./FieldPreview.css";

/** Same control as the mini-app's `FileFieldInput`: «Выберите файл» + «Файл не выбран». */
export function FileFieldPreview({ field }: FieldPreviewProps<FileField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <div className={`input ${styles.fileInput}`}>
        <span className={styles.fileButton}>Выберите файл</span>
        <span className={styles.fileName}>Файл не выбран</span>
      </div>
      <small className={styles.fileLimits}>
        До {field.max_files} файл(ов),{" "}
        {Math.round(field.max_size_bytes / 1024 / 1024)} МБ каждый
      </small>
    </div>
  );
}

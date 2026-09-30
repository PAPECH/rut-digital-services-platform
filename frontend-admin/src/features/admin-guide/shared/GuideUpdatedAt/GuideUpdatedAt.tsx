import * as styles from "./GuideUpdatedAt.css";

/** «Актуально на: ДД.ММ.ГГГГ» — takes an ISO date (`YYYY-MM-DD`). */
export function GuideUpdatedAt({ date }: { date: string }) {
  const [year, month, day] = date.split("-");
  return (
    <footer className={styles.footer}>
      Актуально на: <time dateTime={date}>{`${day}.${month}.${year}`}</time>
    </footer>
  );
}

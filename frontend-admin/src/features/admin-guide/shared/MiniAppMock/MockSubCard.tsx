import * as mock from "./MiniAppMock.css";

/** `.sub-card` with a status `.tag` — «История заявок» and «История прохождения тестов». */
export function MockSubCard({
  name,
  meta,
  status,
  tone,
}: {
  name: string;
  meta: string;
  status: string;
  tone: keyof typeof mock.tagTone;
}) {
  return (
    <div className={mock.subCard}>
      <span>
        <span className={mock.subName}>{name}</span>
        <br />
        <span className={mock.subMeta}>{meta}</span>
      </span>
      <span className={`${mock.tag} ${mock.tagTone[tone]}`}>
        <span className={mock.tagDot} />
        {status}
      </span>
    </div>
  );
}

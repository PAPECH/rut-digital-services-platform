import { DoDontPair } from "../../shared/DoDontPair/DoDontPair";
import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockTile } from "../../shared/MiniAppMock/MockTile";
import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import * as styles from "./StyleGuide.css";

const TILES = [
  { title: "Заселение", icon: "⌂" },
  { title: "Оплата проживания", icon: "₽" },
  { title: "Пропуск", icon: "▣" },
  { title: "Заявки и обращения", icon: "✎" },
];

function Menu({ filled }: { filled: (index: number) => boolean }) {
  return (
    <PhoneMockup title="Главное меню">
      <div className={mock.grid}>
        {TILES.map((tile, index) => (
          <MockTile key={tile.title} title={tile.title} icon={tile.icon} filled={filled(index)} />
        ))}
      </div>
    </PhoneMockup>
  );
}

/** Alternate filled and outline cards, or fill only the key ones; never fill everything. */
export function FillAlternationRule() {
  return (
    <div className={styles.rule}>
      <h3 className={styles.ruleTitle}>Заливка карточек: чередуйте или выделяйте главное</h3>
      <p className={styles.ruleText}>
        Заливка включается в настройках категории: «Цвет карточки» → «Заполнить карточку цветом
        системы?», затем «Сохранить» → «Опубликовать». Чередуйте залитые и обычные карточки, чтобы
        меню читалось ритмично, или залейте одну-две самые важные.
      </p>
      <DoDontPair
        good={{
          example: <Menu filled={(index) => index % 2 === 0} />,
          caption: "Через одну — меню читается ритмично. Или залейте только главный раздел.",
        }}
        bad={{
          example: <Menu filled={() => true} />,
          caption: "Залито всё — ничего не выделено, меню выглядит тяжёлым.",
        }}
      />
    </div>
  );
}

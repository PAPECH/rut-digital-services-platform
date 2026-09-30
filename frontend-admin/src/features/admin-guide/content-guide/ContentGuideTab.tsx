import { GuideSection } from "../shared/GuideSection/GuideSection";
import { GuideTabLayout } from "../shared/GuideTabLayout/GuideTabLayout";
import { BlockCatalog } from "./BlockCatalog/BlockCatalog";
import { FormEmbedGuide } from "./FormEmbedGuide/FormEmbedGuide";
import { CalloutRule } from "./StyleGuide/CalloutRule";
import { FillAlternationRule } from "./StyleGuide/FillAlternationRule";
import { HeadingRule } from "./StyleGuide/HeadingRule";

const SECTIONS = [
  { id: "content-blocks", title: "Блоки страницы" },
  { id: "content-style", title: "Стайл-гайд" },
  { id: "content-forms", title: "Как встроить форму" },
] as const;

export function ContentGuideTab() {
  return (
    <GuideTabLayout tab="content" sections={SECTIONS}>
      <GuideSection
        {...SECTIONS[0]}
        lead="Страница категории собирается из блоков: «Добавить блок» в редакторе категории. Под описанием каждого блока — как он выглядит у пользователя в мини-приложении."
      >
        <BlockCatalog />
      </GuideSection>
      <GuideSection
        {...SECTIONS[1]}
        lead="Единые правила оформления, чтобы все разделы бота выглядели одинаково и читались с первого взгляда."
      >
        <HeadingRule />
        <FillAlternationRule />
        <CalloutRule />
      </GuideSection>
      <GuideSection
        {...SECTIONS[2]}
        lead="Формы создаются в «Конструкторе форм», а на страницу попадают через блоки."
      >
        <FormEmbedGuide />
      </GuideSection>
    </GuideTabLayout>
  );
}

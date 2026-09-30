import { useAuth } from "@/auth/AuthProvider";
import { FaqCollection } from "@/features/faq/ui/FaqCollection";

export function FaqPage() {
  const { profile } = useAuth();
  const isEn =
    profile?.language_code &&
    !profile.language_code.toLowerCase().startsWith("ru");
  return (
    <div className="screen">
      <h1 className="screen-title">{isEn ? "FAQ" : "Частые вопросы"}</h1>
      <p className="screen-sub">
        {isEn
          ? "Tap a question to expand"
          : "Нажмите на вопрос, чтобы развернуть ответ"}
      </p>

      <FaqCollection />
    </div>
  );
}

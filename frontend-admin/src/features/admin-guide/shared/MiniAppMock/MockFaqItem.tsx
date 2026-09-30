import { useState } from "react";

import * as mock from "./MiniAppMock.css";

/** `.faq-item` — one tappable item of «Аккордеон» and «Частые вопросы (FAQ)». */
export function MockFaqItem({
  question,
  answer,
  defaultOpen = false,
}: {
  question: string;
  answer: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={mock.faqItem}>
      <button
        type="button"
        className={mock.faqQuestion}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span>{question}</span>
        <span className={`${mock.faqChevron} ${open ? mock.faqChevronOpen : ""}`} aria-hidden>
          ⌄
        </span>
      </button>
      {open ? <div className={mock.faqAnswer}>{answer}</div> : null}
    </div>
  );
}

import type { ElementGroup } from "@/features/form-tests/model/groupElements";
import { Instruction } from "./Instruction";
import { MultipleChoiceQuestionInput } from "./MultipleChoiceQuestionInput";
import { QuestionnaireTitle } from "./QuestionnaireTitle";
import { ScaleQuestionMatrix } from "./ScaleQuestionMatrix";
import { SectionTitle } from "./SectionTitle";
import { SingleChoiceQuestionInput } from "./SingleChoiceQuestionInput";
import { TextQuestionInput } from "./TextQuestionInput";

export function ElementGroupRegistry({
  group,
  numberByKey,
  answers,
  disabled,
  onChange,
}: {
  group: ElementGroup;
  numberByKey: Map<string, number>;
  answers: Record<string, unknown>;
  disabled: boolean;
  onChange: (key: string, value: unknown) => void;
}) {
  if (group.kind === "scale_matrix") {
    return (
      <ScaleQuestionMatrix
        group={group}
        numberByKey={numberByKey}
        values={answers as Record<string, string | undefined>}
        disabled={disabled}
        onChange={onChange}
      />
    );
  }

  const { element } = group;
  const number = numberByKey.get(element.key);
  switch (element.type) {
    case "questionnaire_title":
      return <QuestionnaireTitle element={element} />;
    case "section_title":
      return <SectionTitle element={element} />;
    case "instruction":
      return <Instruction element={element} />;
    case "text":
      return (
        <TextQuestionInput
          element={element}
          number={number}
          value={answers[element.key] as string | undefined}
          disabled={disabled}
          onChange={(value) => onChange(element.key, value)}
        />
      );
    case "single_choice":
    case "scale":
      return (
        <SingleChoiceQuestionInput
          element={element}
          number={number}
          value={answers[element.key] as string | undefined}
          disabled={disabled}
          onChange={(value) => onChange(element.key, value)}
        />
      );
    case "multiple_choice":
      return (
        <MultipleChoiceQuestionInput
          element={element}
          number={number}
          value={answers[element.key] as string[] | undefined}
          disabled={disabled}
          onChange={(value) => onChange(element.key, value)}
        />
      );
    default:
      return null;
  }
}

import { Icon } from "@/components/Icon";

export function TicketSearchInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="ticket-search">
      <span className="ico"><Icon.Search /></span>
      <input
        className="input"
        value={value}
        placeholder="ФИО или MAX ID"
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

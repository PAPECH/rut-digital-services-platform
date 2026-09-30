import type { ConversationItem } from "@/api/types";

function conversationName(conversation: ConversationItem): string {
  return (
    `${conversation.last_name ?? ""} ${conversation.first_name ?? ""}`.trim() ||
    conversation.username ||
    "Пользователь"
  );
}

export function TicketConversationHeader({
  conversation,
  onOpenProfile,
}: {
  conversation: ConversationItem;
  onOpenProfile: () => void;
}) {
  return (
    <div className="ticket-conversation-head">
      <button className="ticket-user-link" onClick={onOpenProfile}>
        {conversationName(conversation)}
      </button>
      <span className="mono">MAX ID: {conversation.max_user_id}</span>
    </div>
  );
}

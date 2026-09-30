import { api } from "@/api/client";
import { StaffFavoriteStatus } from "@/api/types";

export async function favoriteTicketHandler(
  ticketId: number,
  isFavorite: boolean,
): Promise<StaffFavoriteStatus> {
  return api
    .post<StaffFavoriteStatus>(`/tickets/favorites`, {
      user_id: ticketId,
      is_favorite: !isFavorite,
    })
    .then((response) => response);
}

export async function markTicketAsRead(ticketId: number): Promise<void> {
  await api.post(`/messages/to-user/${ticketId}`, {
    text: "Отмечено как прочитанное",
    mark_as_read: true,
  });
}

import { RefObject } from "react";
import {
  ContextMenuPosition,
  ConversationItem,
} from "@/api/types";
import MenuItem from "./MenuItem";
import {
  favoriteTicketHandler,
  markTicketAsRead,
} from "./FavoriteTicketHandler";

interface ContextMenuProps {
  menuRef: RefObject<HTMLUListElement>;
  position: ContextMenuPosition;
  row_id: number;
  isFavorite: boolean;
  isOpen: boolean;
  closeMenu: () => void;
  setConvs: React.Dispatch<React.SetStateAction<ConversationItem[]>>;
}

function ContextMenu({
  menuRef,
  position,
  row_id,
  isFavorite,
  isOpen,
  closeMenu,
  setConvs,
}: ContextMenuProps) {
  return (
    <ul
      ref={menuRef}
      style={{
        position: "fixed",
        top: position.y,
        left: position.x,
        background: "#fff",
        border: "1px solid #ccc",
        borderRadius: "6px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        listStyle: "none",
        padding: "4px 0",
        margin: 0,
        minWidth: "160px",
        zIndex: 1000,
      }}
    >
      <MenuItem
        onClick={async () => {
          const favoriteStatus = await favoriteTicketHandler(
            row_id,
            isFavorite,
          );
          setConvs((prevConvs) =>
            prevConvs
              .map((conv) =>
                conv.user_id == row_id
                  ? {
                      ...conv,
                      my_favorite: favoriteStatus.my_favorite,
                      is_favorite: favoriteStatus.is_favorite,
                    }
                  : conv,
              )
              .sort((a, b) => {
                if (a.my_favorite !== b.my_favorite) {
                  return a.my_favorite ? -1 : 1;
                }
                return (
                  new Date(b.last_message_at ?? 0).getTime() -
                  new Date(a.last_message_at ?? 0).getTime()
                );
              }),
          );
          closeMenu();
        }}
      >
        {isFavorite ? "💔 Открепить" : "♥️ Закрепить"}
      </MenuItem>
      {isOpen && (
        <MenuItem
          onClick={() => {
            markTicketAsRead(row_id);
            closeMenu();
          }}
        >
          📁 Отметить как прочитанное
        </MenuItem>
      )}
    </ul>
  );
}

export default ContextMenu;

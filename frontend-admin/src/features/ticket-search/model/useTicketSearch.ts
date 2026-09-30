import { useSearchParams } from "react-router-dom";

export function useTicketSearch() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("query") ?? "";
  const requestedUserId = Number(searchParams.get("user")) || null;

  const setQuery = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.delete("user");
    if (value.trim()) next.set("query", value);
    else next.delete("query");
    setSearchParams(next, { replace: true });
  };

  const consumeRequestedUser = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("user");
    setSearchParams(next, { replace: true });
  };

  return { query, requestedUserId, setQuery, consumeRequestedUser };
}

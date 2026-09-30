import { useEffect, useState } from "react";

/** Tracks which guide section is currently at the top of the viewport, for the TOC highlight. */
export function useActiveSection(sectionIds: ReadonlyArray<string>) {
  const [active, setActive] = useState(sectionIds[0] ?? "");

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const visible = new Map<string, boolean>();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => visible.set(entry.target.id, entry.isIntersecting));
        const first = sectionIds.find((id) => visible.get(id));
        if (first) setActive(first);
      },
      { rootMargin: "-80px 0px -60% 0px" },
    );
    sectionIds.forEach((id) => {
      const node = document.getElementById(id);
      if (node) observer.observe(node);
    });
    return () => observer.disconnect();
  }, [sectionIds]);

  return active;
}

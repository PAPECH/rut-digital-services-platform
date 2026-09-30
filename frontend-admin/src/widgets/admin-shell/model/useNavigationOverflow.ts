import { useLayoutEffect, useState } from "react";
import type { RefObject } from "react";

const navigationGap = 2;

export function useNavigationOverflow(
  itemCount: number,
  containerRef: RefObject<HTMLDivElement>,
  measurementRef: RefObject<HTMLDivElement>,
): number {
  const [visibleCount, setVisibleCount] = useState(itemCount);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const measurement = measurementRef.current;
    if (!container || !measurement) return;

    const update = () => {
      const availableWidth = container.getBoundingClientRect().width;
      const itemWidths = Array.from(
        measurement.querySelectorAll<HTMLElement>("[data-navigation-item]"),
      ).map((item) => item.getBoundingClientRect().width);
      const moreWidth =
        measurement
          .querySelector<HTMLElement>("[data-navigation-more]")
          ?.getBoundingClientRect().width ?? 0;
      const allItemsWidth = itemWidths.reduce(
        (total, width, index) =>
          total + width + (index === 0 ? 0 : navigationGap),
        0,
      );

      if (allItemsWidth <= availableWidth) {
        setVisibleCount(itemCount);
        return;
      }

      let usedWidth = 0;
      let nextVisibleCount = 0;
      for (const width of itemWidths) {
        const nextWidth =
          usedWidth + width + (nextVisibleCount === 0 ? 0 : navigationGap);
        if (nextWidth + moreWidth > availableWidth) break;
        usedWidth = nextWidth;
        nextVisibleCount += 1;
      }
      setVisibleCount(nextVisibleCount);
    };

    const observer = new ResizeObserver(update);
    observer.observe(container);
    observer.observe(measurement);
    update();
    void document.fonts?.ready.then(update);

    return () => observer.disconnect();
  }, [containerRef, itemCount, measurementRef]);

  return Math.min(visibleCount, itemCount);
}

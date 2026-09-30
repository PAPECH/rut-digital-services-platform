import { useEffect, useRef } from "react";
import QRCodeStyling from "qr-code-styling";

interface Props {
  value: string;
  size: number;
  color: string;
  /** Optional center logo. Bumps error correction to "Q" so the code stays scannable with a
   * chunk of the center excavated -- plain "M" (used with no logo) doesn't leave enough margin
   * for that. */
  logoSrc?: string;
}

/**
 * QR rendering via `qr-code-styling` (kept over `qrcode.react` for the module-shape options it
 * offers, even though "square" -- plain modules -- is what's actually configured right now).
 * Renders as SVG so it stays crisp at print resolution regardless of on-screen size.
 */
export function StyledQrCode({ value, size, color, logoSrc }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const qrRef = useRef<QRCodeStyling | null>(null);

  useEffect(() => {
    const shared = {
      width: size,
      height: size,
      dotsOptions: { type: "square" as const, color },
      cornersSquareOptions: { type: "square" as const, color },
      cornersDotOptions: { type: "square" as const, color },
      data: value,
      image: logoSrc,
      imageOptions: logoSrc
        ? { imageSize: 0.22, margin: 8, hideBackgroundDots: true, crossOrigin: "anonymous" as const }
        : undefined,
      qrOptions: { errorCorrectionLevel: (logoSrc ? "Q" : "M") as "Q" | "M" },
    };
    if (!qrRef.current) {
      qrRef.current = new QRCodeStyling({
        type: "svg",
        margin: 4,
        backgroundOptions: { color: "#ffffff" },
        ...shared,
      });
      if (containerRef.current) qrRef.current.append(containerRef.current);
      return;
    }
    qrRef.current.update(shared);
  }, [value, size, color, logoSrc]);

  return <div ref={containerRef} className="campaign-link-qr-canvas" />;
}

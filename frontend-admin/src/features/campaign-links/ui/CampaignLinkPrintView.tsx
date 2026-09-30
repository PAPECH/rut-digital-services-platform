import { createPortal } from 'react-dom'

import { Icon } from '@/components/Icon'
import type { CampaignLink } from '@/entities/campaign-links/model/types'
import { StyledQrCode } from '@/features/campaign-links/ui/StyledQrCode'

interface Props {
  link: CampaignLink
  botName: string
  brandColor: string | null
  onClose: () => void
}

function CampaignLinkPoster({
  link,
  botName,
  brandColor,
  id,
}: {
  link: CampaignLink
  botName: string
  brandColor: string | null
  id?: string
}) {
  return (
    <div
      className='campaign-link-print'
      id={id}
      style={brandColor ? ({ '--print-brand': brandColor } as React.CSSProperties) : undefined}>
      <h1 className='campaign-link-print-title'>{botName}</h1>
      {link.bot_username ? <p className='campaign-link-print-username'>@{link.bot_username}</p> : null}
      <div className='campaign-link-print-qr'>
        <StyledQrCode value={link.deep_link} size={600} color='#000000' logoSrc='/max-logo.png' />
      </div>
    </div>
  )
}

/**
 * A4 poster: QR + bot name/username only (Task 026). Printed via the browser's own print-to-PDF
 * flow -- no server-side PDF pipeline. No bot logo, no visible link/UTM text by design -- just
 * the scan target and who it's from. QR dots stay black regardless of brand color (only the
 * frame/title pick it up) -- a light brand color tinting the modules themselves risks scan
 * reliability, which matters more here than matching the palette exactly. The center mark is
 * MAX's own app icon (`public/max-logo.png`, MAX's official apple-touch-icon), not the bot's --
 * it signals "this opens in MAX," matching how MAX/Telegram deep-link QR codes usually look;
 * `StyledQrCode` bumps error correction to Q to keep it scannable with the center excavated.
 *
 * The poster renders twice: once inline here for the on-screen preview, and once portaled into
 * `#print-root` (a body-level sibling of #root, see index.html) purely for `window.print()` to
 * target. Printing the inline copy directly used to either get clipped (ancestor modal chrome has
 * overflow:hidden) or -- once that was fixed -- print a second, blank leading page, because
 * `visibility: hidden` on the rest of the app hides content but doesn't remove it from layout, so
 * everything above the poster in the DOM still pushed it down by its own (invisible) height. The
 * portal copy has no such siblings to be clipped or pushed by.
 */
export function CampaignLinkPrintView({ link, botName, brandColor, onClose }: Props) {
  const printRoot = document.getElementById('print-root')
  return (
    <div className='submission-preview'>
      <section className='submission-preview__dialog campaign-link-print-dialog'>
        <header className='submission-preview__header'>
          <strong>Печать QR-постера</strong>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type='button'
              className='btn btn-secondary btn-sm'
              onClick={() => void navigator.clipboard.writeText(link.deep_link)}>
              Скопировать ссылку
            </button>
            <button type='button' className='btn btn-primary btn-sm' onClick={() => window.print()}>
              Печать
            </button>
            <button className='btn btn-ghost btn-icon' type='button' aria-label='Закрыть' onClick={onClose}>
              <Icon.X />
            </button>
          </div>
        </header>
        <CampaignLinkPoster link={link} botName={botName} brandColor={brandColor} />
      </section>
      {printRoot
        ? createPortal(
            <CampaignLinkPoster
              link={link}
              botName={botName}
              brandColor={brandColor}
              id='campaign-link-print'
            />,
            printRoot,
          )
        : null}
    </div>
  )
}

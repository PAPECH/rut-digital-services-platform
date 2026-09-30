import { useI18n } from '@/i18n'
import { usePlatform } from '@/features/platform-manifest/model/PlatformProvider'

export function Topbar() {
  const { t } = useI18n()
  const { manifest } = usePlatform()
  const configuredLogo = manifest?.bot.branding.logo_url
  const logo = typeof configuredLogo === 'string' && configuredLogo ? configuredLogo : t('logo-miit-white')
  return (
    <></>
    // <header className="topbar">
    //   <img src={logo} alt="" className="topbar__logo" />
    //   {manifest ? (
    //     <strong className="topbar__bot-name">{manifest.bot.name}</strong>
    //   ) : null}
    // </header>
  )
}

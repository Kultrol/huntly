import * as React from "react"

// Match the Tailwind md breakpoint used to show the desktop sidebar.
const MOBILE_QUERY = "(width < 48rem)"

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const media = window.matchMedia(MOBILE_QUERY)
    const sync = () => setIsMobile(media.matches)
    media.addEventListener("change", sync)
    sync()
    return () => media.removeEventListener("change", sync)
  }, [])

  return !!isMobile
}

"use client"

import { Url } from "next/dist/shared/lib/router/router"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { PropsWithChildren, useCallback } from "react"

export default function FromLink(props: { className?: string, href: Url, skeleton?: boolean } & PropsWithChildren) {
  const pathname = usePathname()

  const fromURL = useCallback((href: Url) => {
    const hrefURL = new URL(href.toString(), "http://placeholder.com")
    hrefURL.searchParams.set("from", pathname)
    return hrefURL.pathname + hrefURL.search + hrefURL.hash
  }, [pathname])

  return (
    <Link className={props.className} href={fromURL(props.href)}>
      {props.children}
    </Link>
  )
}

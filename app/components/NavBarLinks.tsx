"use client"

import { useAuth } from "@/context/AuthContext"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useCallback } from "react"

export default function NavBarLinks() {
  const { loggedIn } = useAuth()
  const pathname = usePathname()

  const fromURL = useCallback((href: string) => {
    const hrefURL = new URL(href, "http://placeholder.com")
    hrefURL.searchParams.set("from", pathname)
    return hrefURL.pathname + hrefURL.search + hrefURL.hash
  }, [pathname])

  return (
    <ul>
      <li>
        <Link href="/">home</Link>
      </li>
      {
        !loggedIn &&
        <li>
          <Link href={fromURL("/signup")}>signup</Link>
        </li>
      }
    </ul>
  )
}

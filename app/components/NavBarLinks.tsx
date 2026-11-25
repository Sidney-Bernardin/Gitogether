"use client"

import { useAuth } from "@/context/AuthContext"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useCallback, useTransition } from "react"
import * as auth from "@/lib/requests/auth"

export default function NavBarLinks() {
  const { loggedIn, setAccessToken } = useAuth()
  const pathname = usePathname()

  const [signoutPending, startSignout] = useTransition()
  const signout = (): void => {
    startSignout(async () => {
      await auth.signout()
      setAccessToken(undefined)
    })
  }

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
      {
        loggedIn &&
        <button onClick={signout} disabled={signoutPending}>logout</button>
      }
    </ul>
  )
}

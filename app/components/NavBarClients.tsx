"use client"

import { useAuth } from "@/context/AuthContext"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { ComponentProps, useCallback, useTransition } from "react"
import * as auth from "@/lib/requests/auth"

export function LinksSkeletons() {
  return <ul className="flex gap-5 list-none">
    {Array.from({ length: 3 }, (_, i) =>
      <li key={i} className="bg-pink-900 h-lh w-25 ml-5"></li>)}
  </ul>
}

export function Links(props: ComponentProps<"ul">) {
  const { loggedIn } = useAuth()
  const pathname = usePathname()

  const fromURL = useCallback((href: string) => {
    const hrefURL = new URL(href, "http://placeholder.com")
    hrefURL.searchParams.set("from", pathname)
    return hrefURL.pathname + hrefURL.search + hrefURL.hash
  }, [pathname])

  return <ul {...props} className="flex list-none">
    {
      !loggedIn &&
      <li>
        <Link href={fromURL("/signup")}>login</Link>
      </li>
    }
  </ul>
}

export function SignoutButton() {
  const { loggedIn, setAccessToken } = useAuth()

  const [signoutPending, startSignout] = useTransition()
  const signout = (): void => {
    startSignout(async () => {
      await auth.signout()
      setAccessToken(undefined)
    })
  }

  return <div>
    {
      loggedIn && <button onClick={signout} disabled={signoutPending}>
        logout
      </button>
    }
  </div>
}

import { Suspense } from "react";
import * as NavBarClient from "./NavBarClients";
import Link from "next/link";

export default function NavBar() {
  return (
    <nav className="flex justify-around bg-bg-b">
      <h1>Gitogether</h1>

      <ul>
        <li>
          <Link href="/">home</Link>
        </li>
      </ul>

      <Suspense fallback={<NavBarClient.LinksSkeletons />}>
        <NavBarClient.Links />
      </Suspense>

      <NavBarClient.SignoutButton />
    </nav>
  )
}

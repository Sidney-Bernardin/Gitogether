import { Suspense } from "react";
import NavBarLinks from "./NavBarLinks";

export default function NavBar() {
  return (
    <nav className="flex justify-around">
      <h1>Gitogether</h1>

      <Suspense fallback={<p>buttons...</p>}>
        <NavBarLinks />
      </Suspense>
    </nav>
  )
}

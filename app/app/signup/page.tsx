import SignupForm from "@/components/SignupForm"
import Link from "next/link"
import { Suspense } from "react"

export default async function Signup() {
  return (
    <div>
      <h1>Signup</h1>

      <Link href="/signin" className="underline">
        signin
      </Link>

      <Suspense fallback={<p>signin-form...</p>}>
        <SignupForm />
      </Suspense>
    </div>
  )
}

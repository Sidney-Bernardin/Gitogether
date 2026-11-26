import SignupForm, { FormSkeleton } from "@/components/SignupForm"
import Link from "next/link"
import { Suspense } from "react"

export default function Signup() {
  return (
    <div>
      <h1>Signup</h1>

      <Link href="/signin" className="underline">
        signin
      </Link>

      <Suspense fallback={<FormSkeleton />}>
        <SignupForm />
      </Suspense>
    </div>
  )
}

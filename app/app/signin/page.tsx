import SigninForm from "@/components/SigninForm"
import { FormSkeleton } from "@/components/SignupForm"
import Link from "next/link"
import { Suspense } from "react"

export default async function Signin() {
  return (
    <div>
      <h1>Signin</h1>

      <Link href="/signup" className="underline">
        signup
      </Link>

      <Suspense fallback={<FormSkeleton />}>
        <SigninForm />
      </Suspense>
    </div>
  )
}

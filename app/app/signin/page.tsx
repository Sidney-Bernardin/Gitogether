import SigninForm from "@/components/SigninForm"
import Link from "next/link"
import { Suspense } from "react"

export default async function Signin() {
  return (
    <div>
      <h1>Signin</h1>

      <Link href="/signup" className="underline">
        signup
      </Link>

      <Suspense fallback={<p>signin-form...</p>}>
        <SigninForm />
      </Suspense>
    </div>
  )
}

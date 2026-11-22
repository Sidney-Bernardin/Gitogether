"use client"

import { useAuth } from "@/context/AuthContext"
import { signin } from "@/lib/requests/auth"
import { FormError } from "@/lib/views"
import { SigninForm } from "@/lib/commands"
import Form from "next/form"
import { useRouter, useSearchParams } from "next/navigation"
import { useActionState } from "react"

export default function SigninFormComponent() {
  const { setAccessToken } = useAuth()

  const router = useRouter()
  const searchParams = useSearchParams()

  const [state, action, pending] = useActionState(async (_prev: FormError<SigninForm> | undefined, formData: FormData) => {
    const [newAccessToken, err] = await signin(formData)
    if (err)
      return err

    setAccessToken(newAccessToken)
    router.push(searchParams.get("from") || "/")
  }, undefined)

  return (
    <Form action={action}>
      <input name="username" type="text" placeholder="Username" disabled={pending} />
      {state && state.fieldErrors?.username?.map((err, idx) =>
        <p key={idx}>{err}</p>)}

      <input name="password" type="password" placeholder="Password" disabled={pending} />
      {state && state.fieldErrors?.password?.map((err, idx) =>
        <p key={idx}>{err}</p>)}

      <input type="submit" disabled={pending} />
      {state && state.formErrors?.map((err, idx) =>
        <p key={idx}>{err}</p>)}
    </Form>
  )
}

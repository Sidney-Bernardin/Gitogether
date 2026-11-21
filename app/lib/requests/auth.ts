"use server"

import { cookies } from "next/headers"
import * as z from "zod"
import * as JWT from "jsonwebtoken"
import cache from "../cache"
import { envars } from "../envars"
import { AccessToken, createAccessToken, FormError } from "../views"
import { SigninForm, signinFormSchema, SignupForm, signupFormSchema } from "../commands"
import { Result } from "../errors"
import db, { pg } from "../db/db"
import bcrypt from "bcryptjs"

export async function refresh(): Promise<string | undefined> {
  const cookieStore = await cookies()

  const refreshToken = cookieStore.get("refreshToken")
  if (!refreshToken)
    return undefined

  const accessToken = await cache.getSession(refreshToken.value)
  return signAccessToken(accessToken)
}

export async function signup(formData: FormData): Promise<Result<string, FormError<SignupForm>>> {

  // Parse form data.
  const form = signupFormSchema.safeParse(Object.fromEntries(formData.entries()))
  if (form.error)
    return [undefined, z.flattenError(form.error)]

  const [accessToken, err]: Result<AccessToken, FormError<SignupForm>> = await pg.transaction(async (tx) => {

    // Check if username is taken.
    if (await db.usernameTaken(tx, form.data.username))
      return [undefined, {
        fieldErrors: { username: ["Username taken."] },
      }]

    // Hash password.
    const passwordHash = await bcrypt.hash(form.data.password, await bcrypt.genSalt(12))

    // Create user.
    return [await db.createUser(tx, {
      username: form.data.username,
      password_hash: Buffer.from(passwordHash),
    }), undefined]
  })

  if (err)
    return [undefined, err]

  await createSession(accessToken)
  return [signAccessToken(accessToken), undefined]
}

export async function signin(formData: FormData): Promise<Result<string, FormError<SigninForm>>> {

  const form = signinFormSchema.safeParse(Object.fromEntries(formData.entries()))
  if (form.error)
    return [undefined, z.flattenError(form.error)]

  const user = await db.getUserByUsername(pg, form.data.username)

  if (!user || !(await bcrypt.compare(form.data.password, user.password_hash.toString())))
    return [undefined, {
      fieldErrors: { password: ["That user doesn't exist."] }
    }]

  const accessToken = createAccessToken(user)
  await createSession(accessToken)
  return [signAccessToken(accessToken), undefined]
}

async function createSession(accessToken: AccessToken) {
  const refreshToken = crypto.randomUUID()

  await cache.setSession(refreshToken, accessToken)

  const cookieStore = await cookies()
  cookieStore.set("refreshToken", refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
    maxAge: envars.REFRESH_TOKEN_EXPIRATION_SECONDS,
  })
}

function signAccessToken(accessToken: AccessToken): string {
  return JWT.sign(accessToken, envars.JWT_SECRET, {
    expiresIn: envars.ACCESS_TOKEN_EXPIRATION_SECONDS,
  })
}

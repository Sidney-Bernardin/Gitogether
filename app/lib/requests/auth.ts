"use server"

import { cookies } from "next/headers"
import * as z from "zod"
import * as JWT from "jsonwebtoken"
import cache from "../cache"
import { envars } from "../envars"
import { Session, FormError, createSession } from "../views"
import { SigninForm, signinFormSchema, SignupForm, signupFormSchema } from "../commands"
import { Result } from "../errors"
import db, { pg } from "../db/db"
import bcrypt from "bcryptjs"
import { getRefreshToken } from "./utils"

export async function refresh(): Promise<string | undefined> {
  const refreshToken = await getRefreshToken()
  if (!refreshToken)
    return undefined

  const session = await cache.getRefreshToken(refreshToken.id)
  return signSession(session, envars.ACCESS_TOKEN_EXPIRATION_SECONDS)
}

export async function signup(formData: FormData): Promise<Result<string, FormError<SignupForm>>> {

  // Parse form data.
  const form = signupFormSchema.safeParse(Object.fromEntries(formData.entries()))
  if (form.error)
    return [undefined, z.flattenError(form.error)]

  const [session, err]: Result<Session, FormError<SignupForm>> = await pg.transaction(async (tx) => {

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

  await storeRefreshToken(session)
  const accessToken = signSession(session, envars.ACCESS_TOKEN_EXPIRATION_SECONDS)

  return [accessToken, undefined]
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

  const session = createSession(user)
  await storeRefreshToken(session)
  const accessToken = signSession(session, envars.ACCESS_TOKEN_EXPIRATION_SECONDS)

  return [accessToken, undefined]
}

async function storeRefreshToken(session: Session) {
  await cache.setRefreshToken(session)

  const refreshToken = signSession(session, envars.ACCESS_TOKEN_EXPIRATION_SECONDS)

  const cookieStore = await cookies()
  cookieStore.set("refreshToken", refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
    maxAge: envars.REFRESH_TOKEN_EXPIRATION_SECONDS,
  })
}

function signSession(session: Session, expiresIn: number): string {
  return JWT.sign(session, envars.JWT_SECRET, { expiresIn })
}

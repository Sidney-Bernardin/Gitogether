"use server"

import { cookies } from "next/headers";
import { Session } from "../views";
import { trySync } from "../errors";
import * as JWT from "jsonwebtoken"
import { envars } from "../envars";
import { cache } from "react";
import { connection } from "next/server";

export const getRefreshToken = cache(async (): Promise<Session | undefined> => {
  await connection()

  const cookieStore = await cookies()

  const refreshTokenCookie = cookieStore.get("refreshToken")
  if (!refreshTokenCookie)
    return undefined

  const [refreshToken] = trySync(() => JWT.verify(refreshTokenCookie.value, envars.JWT_SECRET) as Session)
  return refreshToken
})

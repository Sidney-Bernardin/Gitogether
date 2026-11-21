import * as z from "zod"

import { users } from "./db/schema"

export type FormError<T> = {
  fieldErrors?: z.core.$ZodFlattenedError<T>["fieldErrors"]
  formErrors?: string[]
}

export type FullUser = typeof users.$inferSelect

export type AccessToken = {
  userId: FullUser["id"],
  username: FullUser["username"],
  createdAt: FullUser["created_at"]
}

export function createAccessToken(u: Partial<FullUser> & Pick<FullUser, "id" | "username" | "created_at">): AccessToken {
  return {
    userId: u.id,
    username: u.username,
    createdAt: u.created_at,
  }
}

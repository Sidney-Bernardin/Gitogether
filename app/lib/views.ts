import * as z from "zod"

import { users } from "./db/schema"

export type FormError<T> = {
  fieldErrors?: z.core.$ZodFlattenedError<T>["fieldErrors"]
  formErrors?: string[]
}

export type FullUser = typeof users.$inferSelect

export type Session = {
  id: string,
  userId: FullUser["id"],
  username: FullUser["username"],
  createdAt: FullUser["created_at"]
}

export function createSession(u: Partial<FullUser> & Pick<FullUser, "id" | "username" | "created_at">): Session {
  return {
    id: crypto.randomUUID(),
    userId: u.id,
    username: u.username,
    createdAt: u.created_at,
  }
}

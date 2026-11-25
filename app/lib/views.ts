import * as z from "zod"

import { repositories, users } from "./db/schema"

export const domainErrorTypes = ["user_not_found", "username_taken"] as const
type DomainErrorType = typeof domainErrorTypes[number]

export type DomainError = {
  type: DomainErrorType,
  msg: string,
}

export type FormError<T> = {
  fieldErrors?: z.core.$ZodFlattenedError<T>["fieldErrors"]
  formErrors?: string[]
}

export type User = typeof users.$inferSelect
export type UserProfile = Pick<User, "id" | "created_at">

export type Session = {
  id: string,
  userId: User["id"],
  username: User["username"],
  createdAt: User["created_at"]
}

export function createSession(u: Partial<User> & Pick<User, "id" | "username" | "created_at">): Session {
  return {
    id: crypto.randomUUID(),
    userId: u.id,
    username: u.username,
    createdAt: u.created_at,
  }
}

export type Repository = typeof repositories.$inferSelect
export type RepositoryListItem = Pick<Repository, "id" | "reponame">

export type UserRepositories = {
  owned_repositories: RepositoryListItem[];
  shared_repositories: RepositoryListItem[];
}

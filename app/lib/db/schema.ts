import { defineRelations } from "drizzle-orm"
import { pgTable, varchar, bytea, bigint, timestamp, index, text, pgEnum, foreignKey, primaryKey } from "drizzle-orm/pg-core"

export const contributorRole = pgEnum("contributor_role", ["admin", "developer"])

export const users = pgTable("users", {
  id: bigint({ mode: "number" }).generatedAlwaysAsIdentity().primaryKey(),

  username: varchar({ length: 255 }).notNull().unique(),
  password_hash: bytea().notNull(),
  password_salt: bytea().notNull(),

  created_at: timestamp({ mode: "string" }).defaultNow().notNull(),
  updated_at: timestamp({ mode: "string" }).defaultNow().notNull(),
}, (table) => ([
  index("username").on(table.username)
]))

export const repositories = pgTable("repositories", {
  id: bigint({ mode: "bigint" }).generatedAlwaysAsIdentity().primaryKey(),

  reponame: text().notNull(),
  description: text().notNull(),
  private: text().notNull(),
  stars: text().notNull(),
  tags: text().array().notNull(),

  created_at: timestamp({ mode: "string" }).defaultNow().notNull(),
  updated_at: timestamp({ mode: "string" }).defaultNow().notNull(),

  parent_id: bigint({ mode: "bigint" }).notNull(),
  owner_id: bigint({ mode: "bigint" }).notNull()
}, (table) => [
  foreignKey({
    columns: [table.parent_id],
    foreignColumns: [table.parent_id]
  }),
  foreignKey({
    columns: [table.owner_id],
    foreignColumns: [users.id]
  }),
  index("reponame").on(table.reponame)
])

export const repository_contributors = pgTable("repository_contributors", {
  repository_id: bigint({ mode: "bigint" }).notNull(),
  contributor_id: bigint({ mode: "bigint" }).notNull(),

  role: contributorRole(),
}, (table) => [
  foreignKey({
    columns: [table.repository_id],
    foreignColumns: [repositories.id],
  }),
  foreignKey({
    columns: [table.contributor_id],
    foreignColumns: [users.id],
  }),
  primaryKey({ columns: [table.repository_id, table.contributor_id] })
])

export const pull_requests = pgTable("pull_requests", {
  id: bigint({ mode: "bigint" }).generatedAlwaysAsIdentity().primaryKey(),

  title: text().notNull(),
  description: text().notNull(),
  source_branch: text().notNull(),
  target_branch: text().notNull(),

  created_at: timestamp({ mode: "string" }).defaultNow().notNull(),
  updated_at: timestamp({ mode: "string" }).defaultNow().notNull(),

  owner_id: bigint({ mode: "bigint" }).notNull(),
  source_id: bigint({ mode: "bigint" }),
  target_id: bigint({ mode: "bigint" }).notNull(),
}, (table) => [
  foreignKey({
    columns: [table.owner_id],
    foreignColumns: [users.id]
  }),
  foreignKey({
    columns: [table.source_id],
    foreignColumns: [repositories.id]
  }),
  foreignKey({
    columns: [table.target_id],
    foreignColumns: [repositories.id]
  }),
])

export const pr_reviewers = pgTable("pr_reviewers", {
  id: bigint({ mode: "bigint" }).generatedAlwaysAsIdentity().primaryKey(),

  pull_request_id: bigint({ mode: "bigint" }).notNull(),
  reviewer_id: bigint({ mode: "bigint" }).notNull(),
}, (table) => [
  foreignKey({
    columns: [table.pull_request_id],
    foreignColumns: [pull_requests.id]
  }),
  foreignKey({
    columns: [table.reviewer_id],
    foreignColumns: [users.id]
  }),
])

export const relations = defineRelations({ users, repositories, repository_contributors, pull_requests, pr_reviewers }, (r) => ({
  users: {
    owned_repositories: r.many.repositories({
      from: r.users.id,
      to: r.repositories.id,
    }),
    shared_repositories: r.many.repositories({
      from: r.users.id.through(r.repository_contributors.contributor_id),
      to: r.repositories.id.through(r.repository_contributors.repository_id),
    }),
    pull_requests: r.many.pull_requests({
      from: r.users.id.through(r.pr_reviewers.reviewer_id),
      to: r.pull_requests.id.through(r.pr_reviewers.pull_request_id),
    }),
  },
  repositories: {
    parent: r.one.repositories({
      from: r.repositories.parent_id,
      to: r.repositories.id,
    }),
    child: r.one.repositories({
      from: r.repositories.id,
      to: r.repositories.parent_id,
    }),
    owner: r.one.users({
      from: r.repositories.owner_id,
      to: r.users.id,
    }),
    pull_requests: r.many.pull_requests({
      from: r.repositories.id,
      to: r.pull_requests.target_id,
    }),
    contributors: r.many.users({
      from: r.repositories.id.through(r.repository_contributors.repository_id),
      to: r.users.id.through(r.repository_contributors.contributor_id)
    })
  },
  pull_requests: {
    owner: r.one.users({
      from: r.pull_requests.owner_id,
      to: r.users.id,
    }),
    source: r.one.repositories({
      from: r.pull_requests.source_id,
      to: r.repositories.id,
    }),
    target: r.one.repositories({
      from: r.pull_requests.target_id,
      to: r.repositories.id,
    }),
    reviewers: r.many.users({
      from: r.pull_requests.id.through(r.pr_reviewers.pull_request_id),
      to: r.users.id.through(r.pr_reviewers.reviewer_id)
    })
  },
}))

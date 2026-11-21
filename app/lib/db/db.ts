import { drizzle, NodePgDatabase, NodePgTransaction } from "drizzle-orm/node-postgres"
import { envars } from "../envars"
import { relations, users } from "./schema"
import { eq, sql } from "drizzle-orm"
import { AccessToken, createAccessToken } from "../views"

export const pg = drizzle(envars.POSTGRES_DSN, { relations })
await pg.execute(sql`SELECT 1`)

type DB =
  | NodePgDatabase<typeof relations>
  | NodePgTransaction<typeof relations>

const queries = {
  async createUser(db: DB, user: typeof users.$inferInsert): Promise<AccessToken> {
    const [newUser] = await db.insert(users).values(user).returning({
      id: users.id,
      username: users.username,
      created_at: users.created_at,
    })

    return createAccessToken(newUser)
  },

  async usernameTaken(db: DB, username: string): Promise<boolean> {
    let q = db.select({ dumy: sql`1` })
      .from(users)
      .where(eq(users.username, username))
      .limit(1)
      .$dynamic()

    if (db instanceof NodePgTransaction)
      q = q.for("update")

    return (await q).length === 1
  },

  async getUserByUsername(db: DB, username: string) {
    return await db.query.users.findFirst({
      columns: {
        id: true,
        username: true,
        password_hash: true,
        created_at: true,
      },
      where: {
        username: username,
      }
    })
  }
}

export default queries

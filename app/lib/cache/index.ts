import { createClient } from "redis"
import { envars } from "../envars"
import { AccessToken } from "../views"

export const cache = await createClient({ url: envars.REDIS_DSN }).connect()
await cache.ping()


const sessionKey = (refreshToken: string) => `session:${refreshToken}`

const queries = {
  async setSession(refreshToken: string, accessToken: AccessToken): Promise<void> {
    const key = sessionKey(refreshToken)
    await cache.multi()
      .hSet(key, accessToken)
      .expire(key, envars.REFRESH_TOKEN_EXPIRATION_SECONDS)
      .exec()
  },

  async getSession(refreshToken: string): Promise<AccessToken> {
    return await cache.hGetAll(sessionKey(refreshToken)) as unknown as AccessToken
  },
}

export default queries

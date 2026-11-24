import { createClient } from "redis"
import { envars } from "../envars"
import { Session as Session } from "../views"

export const cache = await createClient({ url: envars.REDIS_DSN }).connect()
await cache.ping()


const refreshTokenKey = (id: string) => `refresh_token:${id}`

const queries = {
  async setRefreshToken(refreshToken: Session): Promise<void> {
    const key = refreshTokenKey(refreshToken.id)
    await cache.multi()
      .hSet(key, refreshToken)
      .expire(key, envars.REFRESH_TOKEN_EXPIRATION_SECONDS)
      .exec()
  },

  async getRefreshToken(refreshTokenID: string): Promise<Session> {
    return await cache.hGetAll(refreshTokenKey(refreshTokenID)) as unknown as Session
  },
}

export default queries

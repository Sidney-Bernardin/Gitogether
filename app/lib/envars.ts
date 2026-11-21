import { z } from "zod"

const envarsSchema = z.object({
  JWT_SECRET: z.string(),

  POSTGRES_DSN: z.url(),
  REDIS_DSN: z.url(),

  REFRESH_TOKEN_EXPIRATION_SECONDS: z.coerce.number(),
  ACCESS_TOKEN_EXPIRATION_SECONDS: z.coerce.number(),
})

const envars_ = envarsSchema.safeParse(process.env)
if (!envars_.success)
  throw Error(envars_.error.message)

export const envars = envars_.data

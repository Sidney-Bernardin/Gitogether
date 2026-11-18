import { drizzle } from "drizzle-orm/node-postgres"
import { envars } from "../envars"
import { relations } from "./schema"

export const db = drizzle(envars.POSTGRES_URL, { relations })

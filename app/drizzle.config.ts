import { defineConfig } from "drizzle-kit"

export default defineConfig({
  dialect: "postgresql",
  schema: "./lib/db/schema.ts",
  out: "../services/postgres/migrations",
  dbCredentials: {
    url: process.env.POSTGRES_DSN!,
  }
})

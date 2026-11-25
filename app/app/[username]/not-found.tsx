"use client"

import { useParams } from "next/navigation"

export default function NotFound() {
  const params = useParams<{ username: string }>()

  return (
    <div>
      <h1>User {params.username} was not found!</h1>
    </div>
  )
}

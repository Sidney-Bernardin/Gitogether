import { getUser, getUserRepositories } from "@/lib/requests/users"
import { getRefreshToken } from "@/lib/requests/utils"
import { RepositoryListItem } from "@/lib/views"
import Link from "next/link"
import { notFound } from "next/navigation"
import { ComponentProps, ReactNode, Suspense } from "react"

export default function UserPage(props: PageProps<"/[username]">) {
  return (
    <div>
      <Suspense fallback={<HeaderSkeleton />}>
        <Header params={props.params} />
      </Suspense>
      <hr />
      <Suspense fallback={<RepositoryListSkeleton />}>
        <RepositoryList params={props.params} />
      </Suspense>
    </div>
  )
}

async function Header(props: { params: Promise<{ username: string }> }) {
  const params = await props.params

  const [user, err] = await getUser(params.username)
  if (err) {
    console.log(`==================${err.type === "user_not_found"} ${err.type}`)
    if (err.type === "user_not_found")
      notFound()
    else throw err
  }

  return (
    <div>
      <h1>{params.username}</h1>
      <p>joined {user?.created_at}</p>
    </div>
  )
}

function HeaderSkeleton() {
  return (
    <div className="flex flex-col gap-1 *:bg-pink-900 *:h-lh">
      <div />
      <div />
    </div>
  )
}

async function RepositoryList(props: { params: Promise<{ username: string }> }) {
  const params = await props.params
  const refreshToken = await getRefreshToken()

  const [user, err] = await getUserRepositories(refreshToken, params.username)
  if (err)
    if (err.type === "user_not_found")
      notFound()
    else throw err

  return (
    <ul>
      owned:
      {user.owned_repositories.map((repo, i) =>
        <RepositoryListItem key={i} ownerUsername={params.username} repository={repo} />)}

      <hr />

      shared:
      {user.shared_repositories.map((repo, idx) =>
        <li key={idx}>{repo.reponame}</li>)}
    </ul>
  )
}

function RepositoryListSkeleton() {
  return (
    <div className="flex flex-col gap-1 *:bg-pink-900 *:h-lh">
      <div />
      <div />
      <div />
      <div />
    </div>
  )
}

function RepositoryListItem(props: { ownerUsername: string, repository: RepositoryListItem } & ComponentProps<"li">) {
  return (
    <li {...props}>
      <Link href={`${props.ownerUsername}/${props.repository.reponame}`}>{props.repository.reponame}</Link>
    </li>
  )
}

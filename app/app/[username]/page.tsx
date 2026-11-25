import { getUser, getUserRepositories } from "@/lib/requests/users"
import { getRefreshToken } from "@/lib/requests/utils"
import { notFound } from "next/navigation"
import { Suspense } from "react"

export default function UserPage(props: PageProps<"/[username]">) {
  return (
    <div>
      <Suspense fallback={<p>header...</p>}>
        <Header params={props.params} />
      </Suspense>
      <hr />
      <Suspense fallback={<p>repos...</p>}>
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
      {user.owned_repositories.map((repo, idx) =>
        <li key={idx}>{repo.reponame}</li>)}

      <hr />

      shared:
      {user.shared_repositories.map((repo, idx) =>
        <li key={idx}>{repo.reponame}</li>)}
    </ul>
  )
}

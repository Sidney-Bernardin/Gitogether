import { getUser, getUserRepositories } from "@/lib/requests/users"
import { getRefreshToken } from "@/lib/requests/utils"
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
  const user = await getUser(params.username)

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

  const {
    owned_repositories,
    shared_repositories,
  } = await getUserRepositories(refreshToken, params.username)

  return (
    <ul>
      owned:
      {owned_repositories.map((repo, idx) =>
        <li key={idx}>{repo.reponame}</li>)}

      <hr />

      shared:
      {shared_repositories.map((repo, idx) =>
        <li key={idx}>{repo.reponame}</li>)}
    </ul>
  )
}

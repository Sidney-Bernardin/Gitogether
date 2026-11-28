import { ComponentProps, Suspense } from "react";
import Link from "next/link";
import { getRepositoryPage } from "@/lib/requests/repositories";
import { notFound } from "next/navigation";
import { RepositoryPage } from "@/lib/views";
import { getRefreshToken } from "@/lib/requests/utils";

const buttons = [
  ["code", "/code"],
  ["contributors", "/contrubutors"],
  ["pull requests", "/pull-requests"],
  ["settings", "/settings"],
] as const

export default async function RepositorySideBar(props: { params: LayoutProps<"/[username]/[reponame]">["params"] } & ComponentProps<"div">) {
  const params = await props.params
  const session = await getRefreshToken()

  const repositoryPromise = getRepositoryPage(session, params.username, params.reponame).then(([repository, err]) => {
    if (err)
      if (err.type === "repository_not_found")
        notFound()
      else throw err
    else return repository
  })

  return (
    <div {...props} className="bg-bg-b">
      <Suspense fallback={<HeaderSkeleton />}>
        <Header repository={repositoryPromise} />
      </Suspense>

      <hr />

      <ul className="flex flex-col gap-1">
        {buttons.map((btn, i) =>
          !params
            ? <li key={i} className="bg-pink-900 w-full h-10"></li>
            : <li key={i}>
              <Link href={`/${params.reponame}/${btn[1]}`}><>{btn[0]}</></Link>
            </li>
        )}
      </ul>
    </div>
  )
}

export function RepositorySideBarSkeleton(props: ComponentProps<"div">) {
  return (
    <div {...props} className={`flex flex-col gap-1 bg-pink-900 ${props.className}`} />
  )
}

async function Header(props: { repository: Promise<RepositoryPage> }) {
  const repository = await props.repository

  return (
    <div>
      {repository.reponame}
      {repository.description}
    </div>
  )
}

async function HeaderSkeleton() {
  return (
    <div className="flex flex-col gap-1 *:bg-pink-900 *:h-lh">
      <div />
      <div />
      <div />
    </div>
  )
}

import React, { Suspense } from "react";
import Link from "next/link";

const buttons = [
  ["code", "/code"],
  ["contributors", "/contrubutors"],
  ["pull requests", "/pull-requests"],
  ["settings", "/settings"],
] as const

export default function RepositorySideBar(props: { params: LayoutProps<"/[username]/[reponame]">["params"] } & React.ComponentProps<"div">) {
  return (
    <div {...props}>
      <ul className="flex flex-col gap-1">
        <Suspense>
          <Buttons params={props.params} />
        </Suspense>
      </ul>
    </div>
  )
}

async function Buttons(props: { params?: LayoutProps<"/[username]/[reponame]">["params"] }) {
  const params = await props.params

  return <>
    {buttons.map((btn, i) =>
      !params
        ? <li key={i} className="bg-pink-900 w-full h-10"></li>
        : <li key={i}>
          <Link href={`${params.username}/${btn[1]}`}><>{btn[0]}</></Link>
        </li>
    )}
  </>
}

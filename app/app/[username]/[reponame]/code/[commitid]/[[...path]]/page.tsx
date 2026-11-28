import { Suspense } from "react";

export default function CodePathPage(props: PageProps<"/[username]/[reponame]/code/[commitid]/[[...path]]">) {
  return (
    <div className="flex-1">
      <Suspense fallback={<FilesSkeleton />}>
        <Files params={props.params} />
      </Suspense>
    </div>
  )
}

async function Files(props: { params: PageProps<"/[username]/[reponame]/code/[commitid]/[[...path]]">["params"] }) {
  const params = await props.params

  return (
    <div>
      <p>files for {params.commitid} {params.path}...</p>
      <p>files for {params.commitid} {params.path}...</p>
      <p>files for {params.commitid} {params.path}...</p>
      <p>files for {params.commitid} {params.path}...</p>
      <p>files for {params.commitid} {params.path}...</p>
      <p>files for {params.commitid} {params.path}...</p>
    </div>
  )
}

function FilesSkeleton() {
  return (
    <div className="flex flex-col gap-1 *:bg-pink-900 *:h-lh">
      <div />
      <div />
      <div />
      <div />
      <div />
      <div />
      <div />
    </div>
  )
}

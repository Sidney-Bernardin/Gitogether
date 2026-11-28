import RepositorySideBar, { RepositorySideBarSkeleton } from "@/components/RepositorySideBar";
import { Suspense } from "react";

export default function RepositoryLayout(props: LayoutProps<"/[username]/[reponame]">) {
  return (
    <div className="flex flex-1">
      <Suspense fallback={<RepositorySideBarSkeleton className="w-25" />}>
        <RepositorySideBar params={props.params} />
      </Suspense>
      {props.children}
    </div>
  )
}

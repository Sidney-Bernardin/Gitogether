import RepositorySideBar from "@/components/RepositorySideBar";

export default function RepositoryLayout(props: LayoutProps<"/[username]/[reponame]">) {
  return (
    <div className="flex flex-1">
      <RepositorySideBar className="w-50 bg-bg-b" params={props.params} />
      {props.children}
    </div>
  )
}

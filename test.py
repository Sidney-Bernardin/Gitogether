import pygit2

foo = pygit2.Repository("tmp/foo")
foo_master = foo.lookup_branch("master")
remote = foo.remotes.create("tmp", "/home/sidney/projects/side/Gitogether.git/main/tmp/bar")
t = remote.fetch()

bar = pygit2.Repository("tmp/bar")
bar_master = bar.lookup_branch("feature")
bar_master_commit = bar.get(bar_master.target)

foo.merge_base(foo_master.target, bar_master_commit.id)

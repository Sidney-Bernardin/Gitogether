from typing import Literal

from pydantic import BaseModel

GitService = Literal["git-upload-pack", "git-receive-pack"]


class GitQueryParams(BaseModel):
    service: GitService | None = None


class RepositoryTreeFile(BaseModel):
    type: Literal["tree", "blob"]
    name: str


class RepositoryBlob(BaseModel):
    data: bytes


class RepositoryFiles(BaseModel):
    tree: RepositoryTreeFile | None = None
    blob: RepositoryBlob | None = None
    readme: bytes | None

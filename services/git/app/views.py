from typing import Literal

from pydantic import BaseModel

GitService = Literal["git-upload-pack", "git-receive-pack"]


class GitQueryParams(BaseModel):
    service: GitService | None = None

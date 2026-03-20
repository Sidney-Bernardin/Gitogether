from enum import Enum


class DomainErrorType(Enum):
    USER_NOT_FOUND = 1

    USERNAME_TAKEN = 2
    USERNAME_INVALID = 3
    USERNAME_OR_PASSWORD_INVALID = 4
    PASSWORD_INVALID = 5

    REPOSITORY_NOT_FOUND = 6
    REPOSITORY_NAME_TAKEN = 7
    REPOSITORY_FILE_NOT_FOUND = 8
    REPOSITORY_EMPTY = 9

    CANNOT_FORK_OWN_REPO = 10
    CANNOT_FORK_PRIVATE_REPO = 11


class DomainError(Exception):
    def __init__(self, type: DomainErrorType, msg: str) -> None:
        super().__init__(type.name, msg)
        self.type = type

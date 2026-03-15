from enum import Enum


class DomainErrorType(Enum):
    USERNAME_TAKEN = 1
    USERNAME_INVALID = 2
    USERNAME_OR_PASSWORD_INVALID = 3
    PASSWORD_INVALID = 4

    REPOSITORY_NOT_FOUND = 5
    REPOSITORY_NAME_TAKEN = 6
    REPOSITORY_FILE_NOT_FOUND = 7
    REPOSITORY_EMPTY = 8


class DomainError(Exception):
    def __init__(self, type: DomainErrorType, msg: str) -> None:
        super().__init__(type.name, msg)
        self.type = type

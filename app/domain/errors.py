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


class DomainError(Exception):
    def __init__(self, type: DomainErrorType, msg: str) -> None:
        super().__init__(type.name, msg)
        self.type = type

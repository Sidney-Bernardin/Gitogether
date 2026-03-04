CREATE TABLE users (
    user_id uuid PRIMARY KEY,

    username text NOT NULL,
    password_hash bytea NOT NULL,
    password_salt bytea NOT NULL
);

CREATE TABLE repositories (
    repository_id uuid PRIMARY KEY,

    name text NOT NULL UNIQUE,
    stars int NOT NULL,

    owner_id uuid NOT NULL REFERENCES users(user_id),
    fork_of uuid REFERENCES repositories(repository_id)
);

CREATE TABLE pull_requests (
    pull_request_id uuid PRIMARY KEY,

    complete boolean NOT NULL,
    approved boolean NOT NULL,

    target_repository uuid REFERENCES repositories(repository_id),
    source_repository uuid REFERENCES repositories(repository_id)
);

CREATE TABLE users (
    user_id uuid PRIMARY KEY,

    username text NOT NULL,
    password bytea NOT NULL
);

CREATE TABLE repositories (
    repository_id uuid PRIMARY KEY,

    name text NOT NULL UNIQUE,
    public boolean,
    stars int NOT NULL,

    fork_of uuid REFERENCES repositories(repository_id)
);

CREATE TABLE pull_requests (
    pull_request_id uuid PRIMARY KEY,

    complete boolean NOT NULL,
    approved boolean NOT NULL,

    target_repository uuid REFERENCES repositories(repository_id),
    source_repository uuid REFERENCES repositories(repository_id)
);

CREATE TABLE repository_users (
    repository_id uuid REFERENCES repositories(repository_id),
    user_id uuid REFERENCES users(user_id),

    role text NOT NULL,

    PRIMARY KEY (repository_id, user_id)
);

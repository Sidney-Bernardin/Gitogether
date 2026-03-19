CREATE TABLE users (
    user_id uuid PRIMARY KEY,

    username text NOT NULL,
    password bytea NOT NULL
);

CREATE TABLE repositories (
    repository_id uuid PRIMARY KEY,

    name text NOT NULL,
    public boolean NOT NULL,
    stars int NOT NULL,

    fork_of uuid REFERENCES repositories(repository_id),
    owner_id uuid REFERENCES users(user_id)
);

CREATE TABLE pull_requests (
    pull_request_id uuid PRIMARY KEY,

    complete boolean NOT NULL,
    approved boolean NOT NULL,

    target_repository uuid REFERENCES repositories(repository_id),
    source_repository uuid REFERENCES repositories(repository_id)
);

CREATE TABLE repository_contributors (
    repository_id uuid REFERENCES repositories(repository_id),
    user_id uuid REFERENCES users(user_id),

    role text NOT NULL,

    PRIMARY KEY (repository_id, user_id)
);

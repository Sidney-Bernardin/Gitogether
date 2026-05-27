CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
    user_id uuid PRIMARY KEY,

    username text NOT NULL UNIQUE,
    password bytea NOT NULL
);

CREATE TABLE repositories (
    repository_id uuid PRIMARY KEY,

    reponame text NOT NULL,
    description text NOT NULL,
    private boolean NOT NULL,
    stars int NOT NULL,
    tags text[] NOT NULL,

    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    parent_id uuid REFERENCES repositories(repository_id),
    owner_id uuid NOT NULL REFERENCES users(user_id)
);

CREATE TABLE pull_requests (
    pull_request_id uuid PRIMARY KEY,

    title text NOT NULL,
    description text NOT NULL,

    source_branch text NOT NULL,
    target_branch text NOT NULL,

    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    owner_id uuid NOT NULL REFERENCES users(user_id),
    source_id uuid REFERENCES repositories(repository_id),
    target_id uuid NOT NULL REFERENCES repositories(repository_id)
);

CREATE TABLE pull_request_reviewers (
    pull_request_id uuid REFERENCES pull_requests(pull_request_id),
    reviewer_id uuid REFERENCES users(user_id),

    approval_required boolean NOT NULL,

    PRIMARY KEY (pull_request_id, reviewer_id)
);

CREATE TYPE repository_contributor_role AS ENUM ('admin', 'contributor');

CREATE TABLE repository_contributors (
    repository_id uuid REFERENCES repositories(repository_id),
    user_id uuid REFERENCES users(user_id),

    role repository_contributor_role NOT NULL,

    PRIMARY KEY (repository_id, user_id)
);

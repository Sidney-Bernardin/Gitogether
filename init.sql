CREATE TABLE users (
    user_id uuid PRIMARY KEY,

    username text NOT NULL,
    password_hash bytea NOT NULL,
    password_salt bytea NOT NULL
);

CREATE TABLE repositories (
    repository_id uuid PRIMARY KEY,

    owner uuid REFERENCES users(user_id) NOT NULL
);

CREATE TYPE "contributor_role" AS ENUM('admin', 'developer');--> statement-breakpoint
CREATE TABLE "pr_reviewers" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "pr_reviewers_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"pull_request_id" bigint NOT NULL,
	"reviewer_id" bigint NOT NULL
);
--> statement-breakpoint
CREATE TABLE "pull_requests" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "pull_requests_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"title" text NOT NULL,
	"description" text NOT NULL,
	"source_branch" text NOT NULL,
	"target_branch" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	"owner_id" bigint NOT NULL,
	"source_id" bigint,
	"target_id" bigint NOT NULL
);
--> statement-breakpoint
CREATE TABLE "repositories" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "repositories_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"reponame" text NOT NULL,
	"description" text NOT NULL,
	"private" text NOT NULL,
	"stars" text NOT NULL,
	"tags" text[] NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	"parent_id" bigint NOT NULL,
	"owner_id" bigint NOT NULL
);
--> statement-breakpoint
CREATE TABLE "repository_contributors" (
	"repository_id" bigint,
	"contributor_id" bigint,
	"role" "contributor_role",
	CONSTRAINT "repository_contributors_pkey" PRIMARY KEY("repository_id","contributor_id")
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "users_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"username" varchar(255) NOT NULL UNIQUE,
	"password_hash" bytea NOT NULL,
	"password_salt" bytea NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "reponame" ON "repositories" ("reponame");--> statement-breakpoint
CREATE INDEX "username" ON "users" ("username");--> statement-breakpoint
ALTER TABLE "pr_reviewers" ADD CONSTRAINT "pr_reviewers_pull_request_id_pull_requests_id_fkey" FOREIGN KEY ("pull_request_id") REFERENCES "pull_requests"("id");--> statement-breakpoint
ALTER TABLE "pr_reviewers" ADD CONSTRAINT "pr_reviewers_reviewer_id_users_id_fkey" FOREIGN KEY ("reviewer_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "pull_requests" ADD CONSTRAINT "pull_requests_owner_id_users_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "pull_requests" ADD CONSTRAINT "pull_requests_source_id_repositories_id_fkey" FOREIGN KEY ("source_id") REFERENCES "repositories"("id");--> statement-breakpoint
ALTER TABLE "pull_requests" ADD CONSTRAINT "pull_requests_target_id_repositories_id_fkey" FOREIGN KEY ("target_id") REFERENCES "repositories"("id");--> statement-breakpoint
ALTER TABLE "repositories" ADD CONSTRAINT "repositories_parent_id_repositories_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "repositories"("parent_id");--> statement-breakpoint
ALTER TABLE "repositories" ADD CONSTRAINT "repositories_owner_id_users_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "repository_contributors" ADD CONSTRAINT "repository_contributors_repository_id_repositories_id_fkey" FOREIGN KEY ("repository_id") REFERENCES "repositories"("id");--> statement-breakpoint
ALTER TABLE "repository_contributors" ADD CONSTRAINT "repository_contributors_contributor_id_users_id_fkey" FOREIGN KEY ("contributor_id") REFERENCES "users"("id");
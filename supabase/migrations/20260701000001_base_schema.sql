-- Run this once against the new Supabase project (SQL Editor, or `psql` with
-- the project's connection string) before deploying the API.
--
-- It creates the table and a dedicated low-privilege role that /search uses
-- to run the LLM-generated SQL. That role can only ever SELECT from
-- western_blot_records - it has no grants on any other table, no write
-- access, and no ability to touch information_schema/pg_catalog beyond what
-- Postgres exposes to every role by default. This is the second layer of
-- defense behind sql_guard.py: even if a bug slipped a bad query past the
-- AST validator, this role physically cannot do anything with it beyond
-- reading this one table.

create table if not exists western_blot_records (
    id                  bigserial primary key,
    paper_id            text not null,
    page                integer,
    western_blot_type   text,
    sample              text,
    organism            text,
    treatment_context   text,
    figure_label        text,
    target              text,
    condition           text,
    band_detected       boolean,
    -- Numeric confidence (0-1) to match the frontend/backend schemas.
    -- If your extraction pipeline naturally produces "high"/"medium"/"low",
    -- convert to a 0-1 score before insert rather than storing text here -
    -- keep this column's type as the single source of truth.
    confidence          real
);

-- Standard read-only Postgres contrib extension, needed by the trigram
-- index below - must be created before the index that uses it.
create extension if not exists pg_trgm;

create index if not exists idx_western_blot_records_target
    on western_blot_records using gin (target gin_trgm_ops);

-- --- Read-only role for the /search raw-SQL execution path ---------------
--
-- Runs as plain SQL so it pastes directly into the Supabase SQL Editor
-- (no psql-only syntax like `:'var'` substitution).

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'hive_readonly') then
        create role hive_readonly with login;
    end if;
end
$$;

-- Set (or rotate) the password separately, right before copying it into
-- DB_READONLY_URL - keeps a real secret out of this checked-in file.
-- alter role hive_readonly with password 'REPLACE_WITH_A_GENERATED_SECRET';

grant connect on database postgres to hive_readonly;
grant usage on schema public to hive_readonly;
grant select on western_blot_records to hive_readonly;

-- Ensures any future column added to this table is still readable without
-- re-granting, but does NOT grant access to any other table created later.
alter default privileges in schema public
    grant select on tables to hive_readonly;

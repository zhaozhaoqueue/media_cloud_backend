-- Initial schema for media cloud API

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar NOT NULL,
    avatar_url varchar,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_identities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider varchar NOT NULL,
    openid varchar NOT NULL,
    unionid varchar,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT user_identities_provider_openid_key UNIQUE (provider, openid)
);

CREATE INDEX user_identities_user_id_idx ON user_identities(user_id);

CREATE TABLE spaces (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar NOT NULL,
    owner_id uuid NOT NULL REFERENCES users(id),
    cover_url varchar,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX spaces_owner_id_idx ON spaces(owner_id);

CREATE TABLE space_members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role varchar NOT NULL,
    joined_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT space_members_space_id_user_id_key UNIQUE (space_id, user_id)
);

CREATE INDEX space_members_user_id_idx ON space_members(user_id);

CREATE TABLE space_share_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    share_code varchar NOT NULL,
    expires_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT space_share_codes_share_code_key UNIQUE (share_code)
);

CREATE INDEX space_share_codes_space_id_idx ON space_share_codes(space_id);
CREATE INDEX space_share_codes_expires_at_idx ON space_share_codes(expires_at);

CREATE TABLE files (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    uploader_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name varchar NOT NULL,
    mime_type varchar NOT NULL,
    size bigint NOT NULL,
    storage_key varchar NOT NULL,
    final_url varchar NOT NULL,
    status varchar NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX files_space_id_idx ON files(space_id);
CREATE INDEX files_uploader_id_idx ON files(uploader_id);
CREATE INDEX files_status_idx ON files(status);

CREATE TABLE photos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    file_id uuid NOT NULL REFERENCES files(id) ON DELETE RESTRICT,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name varchar NOT NULL,
    url varchar NOT NULL,
    thumb_url varchar NOT NULL,
    size bigint NOT NULL,
    width int,
    height int,
    thumb_width int,
    thumb_height int,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX photos_space_id_idx ON photos(space_id);
CREATE INDEX photos_owner_id_idx ON photos(owner_id);
CREATE INDEX photos_created_at_idx ON photos(created_at);

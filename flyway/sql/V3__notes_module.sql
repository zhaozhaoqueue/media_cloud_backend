-- Notes module schema

CREATE TABLE notes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title varchar NOT NULL,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    archived_at timestamptz
);

CREATE INDEX notes_owner_id_idx ON notes(owner_id);
CREATE INDEX notes_updated_at_idx ON notes(updated_at DESC);

CREATE TABLE note_members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role varchar NOT NULL,
    joined_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT note_members_note_id_user_id_key UNIQUE (note_id, user_id),
    CONSTRAINT note_members_role_check CHECK (role IN ('owner', 'admin', 'member'))
);

CREATE INDEX note_members_user_id_idx ON note_members(user_id);

CREATE TABLE note_share_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    share_code varchar NOT NULL,
    expires_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    max_uses int,
    used_count int NOT NULL DEFAULT 0,
    CONSTRAINT note_share_codes_share_code_key UNIQUE (share_code),
    CONSTRAINT note_share_codes_max_uses_check CHECK (max_uses IS NULL OR max_uses > 0),
    CONSTRAINT note_share_codes_used_count_check CHECK (used_count >= 0)
);

CREATE INDEX note_share_codes_note_id_idx ON note_share_codes(note_id);
CREATE INDEX note_share_codes_expires_at_idx ON note_share_codes(expires_at);

CREATE TABLE note_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id uuid NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    content text NOT NULL,
    created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    updated_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX note_items_note_id_updated_at_idx ON note_items(note_id, updated_at DESC);

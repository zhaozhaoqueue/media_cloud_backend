ALTER TABLE users
    ADD COLUMN avatar_file_id uuid REFERENCES files(id) ON DELETE SET NULL;

CREATE INDEX users_avatar_file_id_idx ON users(avatar_file_id);

ALTER TABLE files
    ALTER COLUMN space_id DROP NOT NULL;

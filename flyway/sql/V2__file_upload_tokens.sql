ALTER TABLE files
    ADD COLUMN upload_token varchar,
    ADD COLUMN upload_expires_at timestamptz;

CREATE INDEX files_upload_expires_at_idx ON files(upload_expires_at);

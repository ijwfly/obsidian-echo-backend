CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vaults (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'note_state') THEN
       CREATE TYPE note_state AS ENUM ('PENDING', 'CLAIMED', 'DELIVERED');
   END IF;
END
$$;

CREATE TABLE IF NOT EXISTS notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vault_id UUID NOT NULL REFERENCES vaults(id) ON DELETE CASCADE,
  external_id TEXT,
  title TEXT,
  content TEXT NOT NULL,
  state note_state NOT NULL DEFAULT 'PENDING',
  claim_owner TEXT,
  claim_timestamp TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_vault_state ON notes(vault_id, state);

CREATE TABLE IF NOT EXISTS delivery_logs (
  id SERIAL PRIMARY KEY,
  note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  client TEXT,
  event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  details JSONB
);

CREATE TABLE IF NOT EXISTS plugin_clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_identifier TEXT NOT NULL,
  vault_id UUID NOT NULL REFERENCES vaults(id) ON DELETE CASCADE,
  last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


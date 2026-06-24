CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid() if needed later

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- PRIMARY KEY = Automatically indexed
    username  TEXT NOT NULL UNIQUE,  -- UNIQUE = Automatically indexed
    password_hash TEXT NOT NULL,
    scopes    TEXT[] NOT NULL DEFAULT '{}', 
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- does not have any .hex() thats why used UUID, (afa-agadg-agadg-adgda11)
-- convert to str using .hex() in User Repository "afaagadgagadgadgda11"
-- uuid.uuid4 is version 4 just, have nothing to do with bytes

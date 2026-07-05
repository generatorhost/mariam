ALTER TABLE ai_resource_routes
    ADD COLUMN IF NOT EXISTS data_platform TEXT NOT NULL DEFAULT 'DB MARIAM';

ALTER TABLE ai_resource_routes
    ADD COLUMN IF NOT EXISTS fallback_provider_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];

-- Purpose: expand recommendations.text length from 300 to 1000 characters.
-- Up
ALTER TABLE recommendations
    ALTER COLUMN text TYPE VARCHAR(1000);

-- Down (rollback)
-- ALTER TABLE recommendations
--     ALTER COLUMN text TYPE VARCHAR(300);

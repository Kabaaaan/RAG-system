-- Static reference data for normalized dictionaries.
-- Safe to run multiple times.

INSERT INTO resource_types (name) VALUES
    ('article'),
    ('course'),
    ('mautic_email')
ON CONFLICT (name) DO NOTHING;

INSERT INTO recommendation_types (name) VALUES
    ('cold'),
    ('warm'),
    ('hot'),
    ('after_sale')
ON CONFLICT (name) DO NOTHING;

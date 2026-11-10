CREATE ROLE experiment LOGIN PASSWORD 'experiment';
CREATE DATABASE experiment OWNER experiment;
\connect experiment
CREATE TABLE items (id integer PRIMARY KEY, bucket integer NOT NULL, payload text NOT NULL);
INSERT INTO items SELECT i, i % 10000, repeat(md5(i::text), 8) FROM generate_series(1, 700000) AS i;
CREATE INDEX items_bucket_idx ON items(bucket);
ANALYZE items;
GRANT SELECT ON items TO experiment;
SELECT pg_size_pretty(pg_total_relation_size('items')) AS fixture_size, pg_total_relation_size('items') AS fixture_bytes;

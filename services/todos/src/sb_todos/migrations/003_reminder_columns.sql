-- Phase 2f: reminder lead-time on todos.
-- due_time already shipped in the initial schema, so keep this migration focused
-- on the missing reminder lead-time column and make it safe to re-run.

ALTER TABLE todos ADD COLUMN remind_before_minutes INTEGER;

INSERT OR IGNORE INTO schema_migrations (version) VALUES (3);

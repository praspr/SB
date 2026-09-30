-- Phase 2a: goal linkage, JIRA linkage, recurrence, and recurring-instance
-- parent link. Each ALTER is safe to re-run: the migration runner in db.py
-- catches "duplicate column name" and continues.

ALTER TABLE todos ADD COLUMN goal_id INTEGER;
ALTER TABLE todos ADD COLUMN jira_ref TEXT;
ALTER TABLE todos ADD COLUMN recurrence_rule TEXT;
ALTER TABLE todos ADD COLUMN parent_todo_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_todos_goal ON todos(goal_id);
CREATE INDEX IF NOT EXISTS idx_todos_jira_ref ON todos(jira_ref);
CREATE INDEX IF NOT EXISTS idx_todos_parent ON todos(parent_todo_id);

INSERT OR IGNORE INTO schema_migrations (version) VALUES (2);

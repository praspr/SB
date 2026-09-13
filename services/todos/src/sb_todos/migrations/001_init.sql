-- Initial schema for sb-todos

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS todos (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  title          TEXT    NOT NULL,
  description    TEXT,
  priority       INTEGER NOT NULL DEFAULT 4,   -- 1=P1..4=none, matches sb model
  due_date       TEXT,                          -- YYYY-MM-DD
  due_time       TEXT,                          -- HH:MM
  is_completed   INTEGER NOT NULL DEFAULT 0,
  completed_at   TEXT,
  tags           TEXT,                          -- JSON array of strings
  external_source TEXT,                         -- 'jira' | 'manual' | null
  external_ref   TEXT,                          -- 'CXP-45827' or null
  domain         TEXT NOT NULL DEFAULT 'work',  -- work | learning | personal
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_todos_ext
  ON todos(external_source, external_ref)
  WHERE external_ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(is_completed);
CREATE INDEX IF NOT EXISTS idx_todos_due       ON todos(due_date);
CREATE INDEX IF NOT EXISTS idx_todos_domain    ON todos(domain);

INSERT OR IGNORE INTO schema_migrations (version) VALUES (1);

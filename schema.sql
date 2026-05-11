-- =============================================================
-- FlowDesk — PostgreSQL Database Schema
-- =============================================================
-- Purpose:
--   Complete database definition for the FlowDesk task manager.
--   This file recreates the entire schema from scratch.
--
-- Usage:
--   Option 1 — Run from terminal:
--     psql -U postgres -d flowdesk -f schema.sql
--
--   Option 2 — Run from psql shell:
--     \c flowdesk
--     \i /path/to/schema.sql
--
-- Note:
--   SQLAlchemy (via db.create_all()) also creates these tables
--   automatically when the Flask app starts. This file exists for
--   documentation, manual setup, and deployment reference.
--
-- Author:   YOUR NAME
-- Project:  FlowDesk Internship Assignment
-- =============================================================


-- =============================================================
-- SETUP — Drop existing objects if rebuilding from scratch
-- =============================================================
-- Uncomment these lines ONLY when you want a full reset.
-- WARNING: This permanently deletes all data.

-- DROP TABLE IF EXISTS tasks CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TYPE  IF EXISTS priority_enum CASCADE;
-- DROP TYPE  IF EXISTS status_enum CASCADE;
-- DROP FUNCTION IF EXISTS refresh_updated_at CASCADE;


-- =============================================================
-- PART 1 — ENUM TYPES
-- =============================================================
-- Enums enforce valid values at the database level.
-- Even if application code has a bug, the DB rejects bad data.
-- PostgreSQL stores enums efficiently (as integers internally).

-- Priority levels for tasks
CREATE TYPE priority_enum AS ENUM (
    'low',
    'medium',
    'high'
);

-- Lifecycle states for tasks
CREATE TYPE status_enum AS ENUM (
    'pending',       -- task created but not started
    'in_progress',   -- task is being worked on
    'completed'      -- task is finished
);


-- =============================================================
-- PART 2 — USERS TABLE
-- =============================================================
-- Stores registered user accounts.
-- Passwords are NEVER stored here — only bcrypt hashes.

CREATE TABLE IF NOT EXISTS users (

    -- Primary key: auto-incrementing integer
    -- SERIAL is shorthand for INTEGER + SEQUENCE + DEFAULT nextval()
    id            SERIAL          PRIMARY KEY,

    -- Username: 3–80 chars, letters/numbers/underscore/hyphen only
    -- Enforced by application layer — DB enforces NOT NULL + UNIQUE
    username      VARCHAR(80)     NOT NULL,

    -- Email address used for login
    -- Stored in lowercase (normalised in application layer)
    email         VARCHAR(120)    NOT NULL,

    -- Werkzeug bcrypt hash of the password
    -- Format: "pbkdf2:sha256:600000$salt$hash"
    -- 256 chars is enough for any bcrypt output
    password_hash VARCHAR(256)    NOT NULL,

    -- Account creation timestamp, always stored in UTC
    -- TIMESTAMPTZ = timestamp with time zone (best practice)
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- ── Constraints ─────────────────────────────────────────
    -- Unique constraints prevent duplicate accounts
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email    UNIQUE (email),

    -- Check constraints enforce business rules at DB level
    CONSTRAINT chk_users_username_length
        CHECK (LENGTH(username) >= 3 AND LENGTH(username) <= 80),
    CONSTRAINT chk_users_email_format
        CHECK (email LIKE '%@%')   -- Basic format check
);

-- ── Indexes on users ──────────────────────────────────────────
-- Index on email: login queries filter by email constantly
-- Without this index, every login scans the entire users table
CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);

-- Index on username: registration duplicate check
CREATE INDEX IF NOT EXISTS idx_users_username
    ON users(username);

-- ── Comment on table ──────────────────────────────────────────
COMMENT ON TABLE  users                IS 'Registered FlowDesk user accounts';
COMMENT ON COLUMN users.id            IS 'Auto-incrementing primary key';
COMMENT ON COLUMN users.username      IS 'Unique display name, 3-80 chars';
COMMENT ON COLUMN users.email         IS 'Unique email, used for login, stored lowercase';
COMMENT ON COLUMN users.password_hash IS 'Werkzeug bcrypt hash — never store plain passwords';
COMMENT ON COLUMN users.created_at   IS 'UTC timestamp of account creation';


-- =============================================================
-- PART 3 — TASKS TABLE
-- =============================================================
-- Core entity: one row per task, linked to one user.
-- Design decision: tasks belong to exactly one user (no sharing).
-- Sharing would require a task_shares junction table.

CREATE TABLE IF NOT EXISTS tasks (

    id          SERIAL          PRIMARY KEY,

    -- Task title: required, max 200 characters
    title       VARCHAR(200)    NOT NULL,

    -- Optional longer description
    -- TEXT has no length limit (unlike VARCHAR)
    description TEXT,

    -- Priority level: restricted to ENUM values
    -- DEFAULT 'medium' so tasks without priority specified
    -- don't accidentally get treated as high priority
    priority    priority_enum   NOT NULL DEFAULT 'medium',

    -- Lifecycle status: restricted to ENUM values
    status      status_enum     NOT NULL DEFAULT 'pending',

    -- Timestamps
    -- created_at is set once at INSERT and never changes
    -- updated_at is refreshed automatically by trigger (Part 4)
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Foreign key: every task must belong to a user
    -- ON DELETE CASCADE: if a user is deleted, all their tasks
    -- are automatically deleted too (no orphaned rows)
    user_id     INTEGER         NOT NULL
                REFERENCES users(id)
                ON DELETE CASCADE,

    -- ── Constraints ─────────────────────────────────────────
    CONSTRAINT chk_tasks_title_not_empty
        CHECK (LENGTH(TRIM(title)) > 0),

    CONSTRAINT chk_tasks_updated_after_created
        CHECK (updated_at >= created_at)
);

-- ── Indexes on tasks ──────────────────────────────────────────

-- Most important index: nearly every query filters by user_id
-- "Give me all tasks for user 5" — this makes it instant
CREATE INDEX IF NOT EXISTS idx_tasks_user_id
    ON tasks(user_id);

-- Composite index: for queries that filter by both user and status
-- "Give me all COMPLETED tasks for user 5"
-- More selective than user_id alone = faster query
CREATE INDEX IF NOT EXISTS idx_tasks_user_status
    ON tasks(user_id, status);

-- Index on created_at: for ordering tasks newest-first
-- ORDER BY created_at DESC — this avoids a full sort
CREATE INDEX IF NOT EXISTS idx_tasks_created_at
    ON tasks(created_at DESC);

-- Partial index: only indexes pending tasks
-- Useful if your app frequently queries incomplete tasks
-- Takes less space than a full index since completed tasks excluded
CREATE INDEX IF NOT EXISTS idx_tasks_pending
    ON tasks(user_id, created_at DESC)
    WHERE status = 'pending';

-- ── Comments ──────────────────────────────────────────────────
COMMENT ON TABLE  tasks              IS 'Task records belonging to users';
COMMENT ON COLUMN tasks.id          IS 'Auto-incrementing primary key';
COMMENT ON COLUMN tasks.title       IS 'Short task description, required, max 200 chars';
COMMENT ON COLUMN tasks.description IS 'Optional detailed notes, no length limit';
COMMENT ON COLUMN tasks.priority    IS 'Importance level: low, medium, high';
COMMENT ON COLUMN tasks.status      IS 'Lifecycle state: pending, in_progress, completed';
COMMENT ON COLUMN tasks.created_at  IS 'UTC timestamp when task was created, immutable';
COMMENT ON COLUMN tasks.updated_at  IS 'UTC timestamp of last change, auto-updated by trigger';
COMMENT ON COLUMN tasks.user_id     IS 'FK → users.id, CASCADE DELETE';


-- =============================================================
-- PART 4 — TRIGGER: auto-update updated_at
-- =============================================================
-- Why a trigger instead of setting it in Python?
--   The trigger fires for EVERY update — even direct SQL edits,
--   psql commands, or migrations. Python-only updates can be
--   missed if someone edits the DB directly. The trigger is
--   a DB-level guarantee.

-- Step 1: Create the function that sets updated_at to NOW()
CREATE OR REPLACE FUNCTION refresh_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    -- NEW refers to the row being inserted/updated
    -- We overwrite whatever updated_at value was sent
    -- with the current UTC timestamp
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Attach the function to the tasks table
-- BEFORE UPDATE = runs before the UPDATE is written to disk
-- FOR EACH ROW  = runs once per updated row (not once per statement)
CREATE OR REPLACE TRIGGER tasks_auto_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION refresh_updated_at();

-- Verify the trigger exists:
-- SELECT trigger_name, event_manipulation, action_timing
-- FROM information_schema.triggers
-- WHERE event_object_table = 'tasks';


-- =============================================================
-- PART 5 — VIEWS (Read-only summaries, no stored data)
-- =============================================================
-- Views are saved queries. They look like tables but are
-- computed on the fly when queried. Useful for reporting.

-- View: task counts per user
CREATE OR REPLACE VIEW vw_user_task_summary AS
SELECT
    u.id                                          AS user_id,
    u.username,
    COUNT(t.id)                                   AS total_tasks,
    COUNT(t.id) FILTER (WHERE t.status = 'completed')   AS completed,
    COUNT(t.id) FILTER (WHERE t.status = 'in_progress') AS in_progress,
    COUNT(t.id) FILTER (WHERE t.status = 'pending')     AS pending,
    -- Completion percentage: NULLIF prevents division-by-zero
    ROUND(
        COUNT(t.id) FILTER (WHERE t.status = 'completed')::NUMERIC
        / NULLIF(COUNT(t.id), 0) * 100,
        2
    )                                             AS completion_pct
FROM
    users u
    LEFT JOIN tasks t ON t.user_id = u.id
GROUP BY
    u.id, u.username;

COMMENT ON VIEW vw_user_task_summary
    IS 'Per-user task counts and completion percentage';

-- Usage example:
-- SELECT * FROM vw_user_task_summary WHERE user_id = 1;

-- View: tasks with owner username (join pre-built)
CREATE OR REPLACE VIEW vw_tasks_with_owner AS
SELECT
    t.id,
    t.title,
    t.description,
    t.priority,
    t.status,
    t.created_at,
    t.updated_at,
    u.username   AS owner_username,
    u.email      AS owner_email
FROM
    tasks t
    JOIN users u ON u.id = t.user_id;

COMMENT ON VIEW vw_tasks_with_owner
    IS 'Tasks joined with owner username and email';


-- =============================================================
-- PART 6 — USEFUL QUERIES (reference / debugging)
-- =============================================================
-- These are not executed — they are documentation.
-- Uncomment and run manually in psql when needed.

-- ── Check all tables ─────────────────────────────────────────
-- \dt

-- ── Inspect table structure ──────────────────────────────────
-- \d users
-- \d tasks

-- ── Count tasks per user ─────────────────────────────────────
-- SELECT * FROM vw_user_task_summary;

-- ── Find tasks created today ──────────────────────────────────
-- SELECT id, title, status, created_at
-- FROM tasks
-- WHERE created_at::date = CURRENT_DATE
-- ORDER BY created_at DESC;

-- ── Priority distribution for a specific user ─────────────────
-- SELECT priority, COUNT(*) AS count
-- FROM tasks
-- WHERE user_id = 1
-- GROUP BY priority
-- ORDER BY count DESC;

-- ── Average tasks created per day ────────────────────────────
-- SELECT
--     DATE(created_at) AS day,
--     COUNT(*) AS tasks_created
-- FROM tasks
-- GROUP BY day
-- ORDER BY day DESC
-- LIMIT 7;

-- ── Check trigger is working ──────────────────────────────────
-- UPDATE tasks SET title = 'Updated title' WHERE id = 1;
-- SELECT id, title, created_at, updated_at FROM tasks WHERE id = 1;
-- (updated_at should differ from created_at after the update)

-- ── Verify foreign key relationships ─────────────────────────
-- SELECT
--     tc.constraint_name,
--     kcu.column_name,
--     ccu.table_name  AS foreign_table,
--     ccu.column_name AS foreign_column
-- FROM information_schema.table_constraints AS tc
-- JOIN information_schema.key_column_usage AS kcu
--     ON tc.constraint_name = kcu.constraint_name
-- JOIN information_schema.constraint_column_usage AS ccu
--     ON ccu.constraint_name = tc.constraint_name
-- WHERE tc.constraint_type = 'FOREIGN KEY'
--   AND tc.table_name = 'tasks';


-- =============================================================
-- PART 7 — SAMPLE DATA (development only)
-- =============================================================
-- Remove this section before production deployment.
-- Uncomment to pre-populate the database for testing.

-- INSERT INTO users (username, email, password_hash) VALUES
--   ('demo_user',
--    'demo@flowdesk.com',
--    'pbkdf2:sha256:600000$REPLACE_WITH_REAL_HASH');
--
-- INSERT INTO tasks (title, description, priority, status, user_id)
-- VALUES
--   ('Set up Flask project',    'Initialise app factory, blueprints', 'high',   'completed',   1),
--   ('Create database models',  'User and Task SQLAlchemy models',    'high',   'completed',   1),
--   ('Build REST API',          'CRUD endpoints for tasks',           'high',   'in_progress', 1),
--   ('Add WebSocket support',   'Flask-SocketIO real-time events',    'medium', 'pending',     1),
--   ('Write analytics module',  'Pandas + NumPy computations',        'medium', 'pending',     1),
--   ('Design the frontend',     'HTML/CSS/JS dashboard',              'medium', 'pending',     1),
--   ('Write README',            'Setup and usage documentation',      'low',    'pending',     1),
--   ('Deploy to server',        'Optional: Heroku or Render',         'low',    'pending',     1);


-- =============================================================
-- END OF SCHEMA
-- =============================================================
-- To verify everything was created successfully, run:
--   \dt                 -- list tables
--   \d users            -- inspect users table
--   \d tasks            -- inspect tasks table
--   \dT                 -- list custom types (enums)
--   \df                 -- list functions (refresh_updated_at)
--   \dv                 -- list views
-- =============================================================
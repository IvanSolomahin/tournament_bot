CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    participation_confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    slot INTEGER NOT NULL,
    name TEXT NOT NULL,
    contact TEXT NOT NULL,
    club TEXT,
    achievements TEXT,
    username TEXT,
    telegram_id INTEGER,
    confirmed_at TEXT,
    payment_file_id TEXT,
    payment_confirmed_at TEXT,
    checkin_day1_at TEXT,
    checkin_day2_at TEXT,
    UNIQUE (team_id, slot)
);

CREATE INDEX IF NOT EXISTS idx_members_username ON members (username);
CREATE INDEX IF NOT EXISTS idx_members_telegram_id ON members (telegram_id);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    actor_telegram_id INTEGER,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
);

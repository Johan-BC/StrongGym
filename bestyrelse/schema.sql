-- Strong Gym bestyrelsesside - D1-skema
-- Kør: npx wrangler d1 execute stronggym-bestyrelse --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS months (
  month      TEXT PRIMARY KEY,          -- YYYY-MM
  data       TEXT NOT NULL,             -- JSON: medlemmer, løn, variable udgifter, kasse ...
  updated_by TEXT,                      -- e-mail fra Cloudflare Access
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS wishlist (
  id         TEXT PRIMARY KEY,
  data       TEXT NOT NULL,             -- JSON: udstyr, pris, finansiering, prioritet, købt
  updated_by TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  id         INTEGER PRIMARY KEY CHECK (id = 1),
  data       TEXT NOT NULL,             -- JSON: kontingent, buffer, faste poster ...
  updated_by TEXT,
  updated_at TEXT
);

-- Hvem ændrede hvad og hvornår. Skrives af worker'en ved hver ændring.
CREATE TABLE IF NOT EXISTS audit (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  at     TEXT NOT NULL,
  email  TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  data   TEXT
);

-- Bestyrelsesmøder: én række pr. mødedato. data = JSON med tid, sted, status,
-- dagsorden og referat (markdown). Ligger kun her - aldrig i det offentlige repo.
CREATE TABLE IF NOT EXISTS meetings (
  dato       TEXT PRIMARY KEY,          -- YYYY-MM-DD
  data       TEXT NOT NULL,
  updated_by TEXT,
  updated_at TEXT
);

-- Opgaver fra referaternes handlingslister. id = mødedato + løbenummer (2026-11-19-01).
CREATE TABLE IF NOT EXISTS tasks (
  id         TEXT PRIMARY KEY,
  data       TEXT NOT NULL,             -- JSON: tekst, ansvarlig, deadline, status, punkt, moede
  updated_by TEXT,
  updated_at TEXT
);

-- Bestyrelsens medlemmer (navn, e-mail, rolle). Fyldes direkte i databasen,
-- aldrig fra repoet. Samme e-mails skal stå i BOARD_EMAILS og i Access-politikken.
CREATE TABLE IF NOT EXISTS board_members (
  email      TEXT PRIMARY KEY,
  navn       TEXT NOT NULL,
  rolle      TEXT,
  updated_at TEXT
);

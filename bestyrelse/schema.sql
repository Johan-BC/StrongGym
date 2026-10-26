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

DROP TABLE IF EXISTS fault_codes;
DROP TABLE IF EXISTS parts;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    plate TEXT NOT NULL,
    vin TEXT,
    mileage INTEGER NOT NULL,
    engine TEXT,
    fuel_type TEXT NOT NULL
        CHECK (fuel_type IN ('petrol', 'diesel', 'hybrid', 'electric')),
    problem TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Received'
        CHECK (status IN ('Received', 'Diagnosnig', 'Waiting for parts', 'Repairing', 'Ready', 'Picked up')),
    date_received TEXT NOT NULL,
    labor_cost REAL NOT NULL DEFAULT 0,
    status_changed_at TEXT NOT NULL DEFAULT (datetime('now')),    
    created_at TEXT NOT NULL DEFAULT (datetime('now')),     
    created_by INTEGER REFERENCES users (id)  
    );

CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price REAL NOT NULL DEFAULT 0
);

CREATE INDEX idx_jobs_plate ON jobs (plate);
CREATE INDEX idx_jobs_status on jobs (status);
import os
import sqlite3
from datetime import datetime

import click
from flask import current_app, g

# Child tables first, so no foreign key points at a dropped table.
TABLES_CHILD_FIRST = [
    "photos", "status_history", "fault_codes", "parts", "notes", "jobs", "users",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def add_missing_column(db, table, column, definition):
    """Add a column if the table lacks it. All arguments are fixed strings from code."""
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
    if column in columns:
        return
    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def run_sql_file(db, name):
    """Run one of the bundled SQL files."""
    with current_app.open_resource(name) as f:
        db.executescript(f.read().decode("utf8"))

def migrate_db():
    """Add any missing tables, indexes and columns. Never deletes data, safe to run repeatedly."""
    db = get_db()
    run_sql_file(db, "schema.sql")
    add_missing_column(db, "jobs", "labor_cost", "REAL NOT NULL DEFAULT 0")
    # Plain TEXT: SQLite refuses a datetime('now') default in ALTER TABLE.
    add_missing_column(db, "jobs", "status_changed_at", "TEXT")
    run_sql_file(db, "migrations.sql")
    db.commit()

def backup_target(prefix, extension):
    """Return a new timestamped file path in instance/backups, creating the folder."""
    backups = os.path.join(current_app.instance_path, "backups")
    os.makedirs(backups, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(backups, f"{prefix}_{stamp}.{extension}")

def init_db():
    """Drop every table, then build a fresh database."""
    db = get_db()
    for name in TABLES_CHILD_FIRST:
        db.execute("DROP TABLE IF EXISTS " + name)
    db.commit()
    migrate_db()


@click.command("init-db")
def init_db_command():
    """Delete existing data and create fresh tables."""
    click.confirm("This deletes ALL data. Continue?", abort=True)
    init_db()
    click.echo("Initialized the database.")

@click.command("migrate-db")
def migrate_db_command():
    """Add missing tables and columns without deleting any data."""
    migrate_db()
    click.echo("Database is up to date.")

@click.command("backup-db")
def backup_db_command():
    """Save a copy of the database into instance/backups."""
    target = backup_target("wrenchtrack", "sqlite")

    copy = sqlite3.connect(target)
    get_db().backup(copy)
    copy.close()
    click.echo(f"Backup saved: {target}")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
    app.cli.add_command(backup_db_command)


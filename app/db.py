import os
import sqlite3
from datetime import datetime

import click
from flask import current_app, g


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

def migrate_db():
    """Add any missing tables. Never deletes data."""
    db = get_db()
    with current_app.open_resource("migrations.sql") as f:
        db.executescript(f.read().decode("utf8"))

    columns = [row["name"] for row in db.execute("PRAGMA table_info(jobs)")]
    if "labor_cost" not in columns:
        db.execute("ALTER TABLE jobs ADD COLUMN labor_cost REAL NOT NULL DEFAULT 0")
        db.commit()        

def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))
    migrate_db()    


@click.command("init-db")
def init_db_command():
    """Delete existing data and create fresh tables."""
    click.confirm("This deletes ALL data. Continue?", abort=True)
    init_db()
    click.echo("Initialized the database.")

@click.command("migrate-db")
def migrate_db_command():
    """Add missing tables without deleting any data."""
    migrate_db()
    click.echo("Database is up to date")

@click.command("backup-db")
def backup_db_command():
    """Save a copy of the database into instance/backups."""
    backups = os.path.join(current_app.instance_path, "backups")
    os.makedirs(backups, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = os.path.join(backups, f"wrenchtrack_{stamp}.sqlite")

    copy = sqlite3.connect(target)
    get_db().backup(copy)
    copy.close()
    click.echo(f"Backup saved: {target}")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
    app.cli.add_command(backup_db_command)


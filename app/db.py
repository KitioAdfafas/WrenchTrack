import sqlite3

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

def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))
    migrate_db()    


@click.command("init-db")
def init_db_command():
    """Delete existing data and create fresh tables."""
    init_db()
    click.echo("Initialized the database.")

@click.command("migrate-db")
def migrate_db_command():
    """Add missing tables without deleting any data."""
    migrate_db()
    click.echo("Database is up to date")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
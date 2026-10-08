import sqlite3

import click
from werkzeug.security import generate_password_hash

from .db import get_db


@click.command("create-user")
@click.argument("username")
@click.password_option()
def create_user_command(username, password):
    """Create a new user. The password is asked for securely."""
    username = username.strip()
    if len(username) < 3:
        raise click.ClickException("Username must be at least 3 characters.")
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")


    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise click.ClickException(f"User '{username}' already exists.")  

    click.echo(f"Created user '{username}'.")


def init_app(app):
    app.cli.add_command(create_user_command)      
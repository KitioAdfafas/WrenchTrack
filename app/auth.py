import sqlite3

import click
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash,generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)

PUBLIC_ENDPOINTS = {"auth.login", "health", "static"}

@click.command("create-user")
@click.argument("username")
def create_user_command(username):
    """Create a new user. The password is asked for securely."""
    username = username.strip()
    if len(username) < 3:
        raise click.ClickException("Username must be at least 3 characters.")

    db = get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing is not None:
        raise click.ClickException(f"User '{username}' already exists.")

    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise click.ClickException(f"User '{username}' already exists.")

    click.echo(f"Created user '{username}'.")

@click.command("reset-password")
@click.argument("username")
def reset_password_command(username):
    """Set a new password for an existing user."""
    db = get_db()
    user = db.execute(
        "SELECT id FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    if user is None:
        raise click.ClickException(f"User '{username}' does not exist.")

    password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(password), user["id"]),
    )
    db.commit()
    click.echo(f"Password changed for '{username}'.")

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()

@bp.before_app_request
def require_login():
    if g.user is None and request.endpoint not in PUBLIC_ENDPOINTS:
        return redirect(url_for("auth.login"))

@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("home"))

    return render_template("auth/login.html")

@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("auth.login")) 

def init_app(app):
    app.register_blueprint(bp)
    app.cli.add_command(create_user_command)
    app.cli.add_command(reset_password_command)
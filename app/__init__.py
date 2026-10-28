import os

from flask import Flask, redirect, url_for
from flask_wtf.csrf import CSRFProtect, generate_csrf
from markupsafe import Markup

from . import auth, db, jobs

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and set a real value"
        )

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        DATABASE=os.path.join(app.instance_path, "wrenchtrack.sqlite"),
        SHOP_TIMEZONE=os.environ.get("SHOP_TIMEZONE", "Europe/Skopje"),
        CURRENCY=os.environ.get("CURRENCY", "MKD"),
        SESSION_COOKIE_SAMESITE="Lax",
        WTF_CSRF_TIME_LIMIT=None,
    )

    os.makedirs(app.instance_path, exist_ok=True)

    csrf.init_app(app)
    app.jinja_env.globals["csrf_field"] = lambda: Markup(
        f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">'
    )

    db.init_app(app)
    auth.init_app(app)
    app.register_blueprint(jobs.bp)

    @app.route("/")
    def home():
        return redirect(url_for("jobs.dashboard"))

    @app.route("/health")
    def health():
        return "WrenchTrack is running"

    return app
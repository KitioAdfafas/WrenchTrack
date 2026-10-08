import os

from flask import Flask

from . import auth, db


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
    )

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    auth.init_app(app)

    @app.route("/health")
    def health():
        return "WrenchTrack is running"

    return app
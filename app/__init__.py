"""Flask application factory."""
import os
from flask import Flask

from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the downloads directory exists
    os.makedirs(app.config["DOWNLOAD_DIR"], exist_ok=True)

    from app.routes import main
    app.register_blueprint(main)

    return app